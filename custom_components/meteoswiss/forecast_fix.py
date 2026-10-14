"""Work around a MeteoSwiss app-API caching regression.

Root cause (diagnosed 2026-10-14)
----------------------------------
``hamsclientfork.meteoSwissClient.get_forecast`` does a single ``GET`` on
``https://app-prod-ws.meteoswiss-app.ch/v2/forecast`` and immediately calls
``response.json()``.  Since ~2026-10-14 the MeteoSwiss CDN serves *two*
representations of the very same forecast object from the same cache key: the
expected ``application/json`` body and an ``application/xhtml+xml`` body
(``<Forecast>…</Forecast>``).  The cache advertises ``Vary: Accept-Encoding``
only -- it does **not** vary on ``Accept`` -- so byte-identical requests come
back as JSON or XHTML essentially at random, depending on which cache node is
hit.  When the library lands on the XHTML variant, ``response.json()`` raises
``requests.exceptions.JSONDecodeError: Expecting value: line 1 column 1``.

The data itself is fine and ``/v2/forecast`` is not retired, so the robust fix
is to retry the request until we land on a JSON node, and to fall back to the
last good forecast for a while if every attempt in one update cycle loses the
coin toss.  This lives in the integration (not in hamsclientfork) because Home
Assistant reinstalls the pinned library on every start.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests  # type: ignore[import-untyped]
from hamsclientfork.client import JSON_FORECAST_URL

_LOGGER = logging.getLogger(__name__)

# How long a previously fetched forecast may be reused when every fresh attempt
# fails, before we give up and raise.
MAX_STALE_SECONDS = 6 * 60 * 60

# Per-update retry budget and spacing.  The XHTML/JSON split is roughly a coin
# toss per request, so a handful of tries makes an all-XHTML cycle very
# unlikely; the small sleep lets us hit a different cache node.
MAX_ATTEMPTS = 8
RETRY_SLEEP_SECONDS = 0.6
REQUEST_TIMEOUT = 10

# Header sets to try, in order.  The decisive factor is ``Accept:
# application/json`` (the only thing that nudges the origin toward JSON); the
# User-Agent does not reliably matter, but we rotate between the MeteoSwiss app
# UA and the library's historical desktop UA in case the origin behaviour
# changes again.
_HEADER_SETS: tuple[dict[str, str], ...] = (
    {
        "User-Agent": "MeteoSwissApp-3.0-Android",
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/1337 Safari/537.36"
        ),
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Encoding": "gzip, deflate",
    },
)


def patch_client(client: Any) -> None:
    """Replace ``client.get_forecast`` with a cache-resilient version.

    The replacement is installed as an instance attribute, so it also shadows
    the internal ``self.get_forecast()`` call made by ``get_data``.
    """

    # Closure-held cache of the last good forecast for this client instance.
    last_good: dict[str, Any] = {"forecast": None, "timestamp": 0.0}

    def get_forecast() -> dict[str, Any]:
        url = JSON_FORECAST_URL.format(client._postCode)
        reasons: list[str] = []

        for attempt in range(1, MAX_ATTEMPTS + 1):
            headers = _HEADER_SETS[(attempt - 1) % len(_HEADER_SETS)]
            try:
                response = requests.get(
                    url, headers=headers, timeout=REQUEST_TIMEOUT
                )
            except requests.RequestException as exc:
                reasons.append(f"attempt {attempt}: request error: {exc}")
                time.sleep(RETRY_SLEEP_SECONDS)
                continue

            status = response.status_code
            content_type = response.headers.get("Content-Type", "")

            if status != 200:
                snippet = response.text[:200].replace("\n", " ")
                reasons.append(
                    f"attempt {attempt}: HTTP {status} "
                    f"content-type={content_type!r} body[:200]={snippet!r}"
                )
                time.sleep(RETRY_SLEEP_SECONDS)
                continue

            try:
                data = response.json()
            except ValueError:
                snippet = response.text[:200].replace("\n", " ")
                reasons.append(
                    f"attempt {attempt}: non-JSON body status={status} "
                    f"content-type={content_type!r} body[:200]={snippet!r}"
                )
                time.sleep(RETRY_SLEEP_SECONDS)
                continue

            if not isinstance(data, dict) or not data.get("plz"):
                shape = (
                    f"keys={sorted(data)[:8]}"
                    if isinstance(data, dict)
                    else f"type={type(data).__name__}"
                )
                reasons.append(
                    f"attempt {attempt}: JSON without usable 'plz' ({shape})"
                )
                time.sleep(RETRY_SLEEP_SECONDS)
                continue

            # Success: a non-empty JSON dict carrying a truthy "plz".
            if attempt > 1:
                _LOGGER.debug(
                    "MeteoSwiss forecast obtained on attempt %d/%d",
                    attempt,
                    MAX_ATTEMPTS,
                )
            client._forecast = data
            last_good["forecast"] = data
            last_good["timestamp"] = time.time()
            return data

        # Every attempt this cycle failed.  Reuse the last good forecast if it
        # is still fresh enough.
        collected = "; ".join(reasons)
        if last_good["forecast"] is not None:
            age = time.time() - last_good["timestamp"]
            if age <= MAX_STALE_SECONDS:
                _LOGGER.warning(
                    "Reusing cached MeteoSwiss forecast (%.0f s old) after %d "
                    "failed attempts: %s",
                    age,
                    MAX_ATTEMPTS,
                    collected,
                )
                client._forecast = last_good["forecast"]
                return last_good["forecast"]

        raise RuntimeError(
            "Could not obtain a JSON forecast from MeteoSwiss after "
            f"{MAX_ATTEMPTS} attempts and no usable cache is available: "
            f"{collected}"
        )

    client.get_forecast = get_forecast
