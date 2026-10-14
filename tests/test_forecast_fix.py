"""Tests for the MeteoSwiss forecast caching work-around.

These exercise ``patch_client`` against a mocked ``requests.get`` so they run
without network access.  They cover the four behaviours of the patched
``get_forecast``:

* a valid JSON body on the first try;
* an empty/XHTML body first, then a valid JSON body (the real CDN symptom);
* total failure while a recent good forecast exists (cache is reused);
* total failure with no cache available (``RuntimeError``).
"""

from __future__ import annotations

import importlib.util
import pathlib
from types import SimpleNamespace
from unittest import mock

import pytest

# Load forecast_fix.py directly from disk.  Importing it through the
# ``custom_components.meteoswiss`` package would execute that package's
# __init__, which pulls in Home Assistant; the work-around itself only needs
# ``requests`` and ``hamsclientfork``, so we load it in isolation.
_MODULE_PATH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "custom_components"
    / "meteoswiss"
    / "forecast_fix.py"
)
_spec = importlib.util.spec_from_file_location("meteoswiss_forecast_fix", _MODULE_PATH)
assert _spec is not None and _spec.loader is not None
forecast_fix = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(forecast_fix)

VALID_FORECAST = {
    "plz": 120100,
    "currentWeather": {"icon": 1, "temperature": 21.4},
    "regionForecast": [],
    "graph": {},
}

# The XHTML variant the CDN sometimes returns in place of JSON.
XHTML_BODY = "<Forecast><currentWeather><icon>1</icon></currentWeather></Forecast>"


class FakeResponse:
    """Minimal stand-in for ``requests.Response``."""

    def __init__(self, *, json_data=None, text="", status=200, content_type):
        self._json_data = json_data
        self.text = text
        self.status_code = status
        self.headers = {"Content-Type": content_type}

    def json(self):
        if self._json_data is None:
            raise ValueError("Expecting value: line 1 column 1 (char 0)")
        return self._json_data


def json_response(data=VALID_FORECAST):
    return FakeResponse(json_data=data, content_type="application/json")


def xhtml_response():
    return FakeResponse(text=XHTML_BODY, content_type="application/xhtml+xml")


def make_client():
    client = SimpleNamespace(_postCode=1201, _forecast=None)
    forecast_fix.patch_client(client)
    return client


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    """Keep the retry loop instant."""
    monkeypatch.setattr(forecast_fix.time, "sleep", lambda _s: None)


def test_valid_json_first_try():
    client = make_client()
    with mock.patch.object(
        forecast_fix.requests, "get", return_value=json_response()
    ) as get:
        result = client.get_forecast()
    assert result == VALID_FORECAST
    assert client._forecast == VALID_FORECAST
    assert get.call_count == 1


def test_xhtml_then_valid_json():
    client = make_client()
    responses = [xhtml_response(), json_response()]
    with mock.patch.object(
        forecast_fix.requests, "get", side_effect=responses
    ) as get:
        result = client.get_forecast()
    assert result == VALID_FORECAST
    assert client._forecast == VALID_FORECAST
    assert get.call_count == 2


def test_failure_reuses_cached_forecast():
    client = make_client()

    # First update succeeds and populates the cache.
    with mock.patch.object(
        forecast_fix.requests, "get", return_value=json_response()
    ):
        client.get_forecast()

    # Second update: every attempt returns XHTML, so the cached value is used.
    with mock.patch.object(
        forecast_fix.requests,
        "get",
        return_value=xhtml_response(),
    ) as get:
        result = client.get_forecast()

    assert result == VALID_FORECAST
    assert client._forecast == VALID_FORECAST
    assert get.call_count == forecast_fix.MAX_ATTEMPTS


def test_stale_cache_is_not_reused():
    client = make_client()
    with mock.patch.object(
        forecast_fix.requests, "get", return_value=json_response()
    ):
        client.get_forecast()

    # Age the cached forecast past the staleness window.
    now = forecast_fix.time.time()
    with mock.patch.object(
        forecast_fix.time,
        "time",
        return_value=now + forecast_fix.MAX_STALE_SECONDS + 1,
    ):
        with mock.patch.object(
            forecast_fix.requests, "get", return_value=xhtml_response()
        ):
            with pytest.raises(RuntimeError):
                client.get_forecast()


def test_failure_without_cache_raises():
    client = make_client()
    with mock.patch.object(
        forecast_fix.requests, "get", return_value=xhtml_response()
    ) as get:
        with pytest.raises(RuntimeError) as excinfo:
            client.get_forecast()
    assert get.call_count == forecast_fix.MAX_ATTEMPTS
    # The collected diagnostics should mention the content type we saw.
    assert "application/xhtml+xml" in str(excinfo.value)


def test_non_dict_json_is_rejected():
    client = make_client()
    with mock.patch.object(
        forecast_fix.requests,
        "get",
        return_value=json_response(data=["not", "a", "dict"]),
    ):
        with pytest.raises(RuntimeError):
            client.get_forecast()
