"""Readings at a point from the MeteoSwiss weather radar.

MeteoSwiss publishes its radar composites as open data: 1 km grids over
Switzerland and its surroundings, one ODIM HDF5 file per product and
5-minute interval, usually online well under two minutes after the interval
ends.  That is much faster than any station feed.  The products read here:

- RZC, the rain rate in mm/h: the quickest "is it raining here right now"
  signal available.
- POH, the probability of hail, and MESHS, the maximum expected hail size,
  which is only ever reported from 20 mm up.

See https://opendatadocs.meteoswiss.ch/d-radar-data
"""

from __future__ import annotations

import asyncio
import datetime
import io
import json
import logging
import math
import typing
from dataclasses import dataclass

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from custom_components.meteoswiss.const import DOMAIN, USER_AGENT

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://data.geo.admin.ch/{collection}/{day}/{name}"
ITEM_URL = "https://data.geo.admin.ch/api/stac/v1/collections/{collection}/items/{day}"
SLOT = datetime.timedelta(minutes=5)
# How often to look for new images.  Only a new image is downloaded
# (20 to 30 kB); a look for one that is not out yet is a single 403.
POLL_INTERVAL = datetime.timedelta(minutes=1)
# An image still missing this long after its usual delay is looked up in
# the day's index, in case its name carries an unusual variant.
OVERDUE = datetime.timedelta(minutes=2)
# Past this age a reading is no longer "now", so its sensor goes
# unavailable instead of repeating it.
MAX_AGE = datetime.timedelta(minutes=20)


@dataclass(frozen=True)
class RadarProduct:
    """One radar product, one file per 5-minute interval.

    A file is named stem + variant + ext.  The stem carries the product
    and the end of the interval (t, and doy its day of the year).  The
    variant is usually the default, but it encodes how the image was
    made - for RZC which radars contributed, "vl" meaning all of them -
    so it changes while a radar is out, for hours at a time.
    """

    collection: str
    stem: str
    variant: str
    ext: str
    # Images appear this long after their interval ends, give or take.
    delay: datetime.timedelta
    # Multiplier from the value stored in the file to the sensor's unit.
    scale: float = 1.0


PRECIPITATION = "precipitation"
HAIL_PROBABILITY = "hail_probability"
HAIL_SIZE = "hail_size"

PRODUCTS: dict[str, RadarProduct] = {
    PRECIPITATION: RadarProduct(
        collection="ch.meteoschweiz.ogd-radar-precip",
        stem="rzc{t:%y}{doy:03d}{t:%H%M}",
        variant="vl",
        ext=".001.h5",
        delay=datetime.timedelta(seconds=30),
    ),
    HAIL_PROBABILITY: RadarProduct(
        collection="ch.meteoschweiz.ogd-radar-hail",
        stem="bzc{t:%y}{doy:03d}{t:%H%M}",
        variant="vl",
        ext=".845.h5",
        delay=datetime.timedelta(seconds=30),
        # Stored as a fraction, 0 to 1.
        scale=100.0,
    ),
    HAIL_SIZE: RadarProduct(
        collection="ch.meteoschweiz.ogd-radar-hail",
        stem="mzc{t:%y}{doy:03d}{t:%H%M}",
        variant="vl",
        ext=".850.h5",
        delay=datetime.timedelta(seconds=30),
    ),
}


def wgs84_to_lv95(lat: float, lon: float) -> tuple[float, float]:
    """Convert WGS84 degrees to Swiss LV95 (east, north) metres.

    swisstopo's approximate formulas.  Within 10 m of the exact projection
    across the whole radar grid, against 1000 m pixels.
    """
    phi = (lat * 3600 - 169028.66) / 10000
    lam = (lon * 3600 - 26782.5) / 10000
    east = (
        2600072.37
        + 211455.93 * lam
        - 10938.51 * lam * phi
        - 0.36 * lam * phi**2
        - 44.54 * lam**3
    )
    north = (
        1200147.07
        + 308807.95 * phi
        + 3745.25 * lam**2
        + 76.63 * phi**2
        - 194.56 * lam**2 * phi
        + 119.79 * phi**3
    )
    return east, north


def latest_slot(product: RadarProduct, now: datetime.datetime) -> datetime.datetime:
    """Return the end of the newest interval whose image may be out by now."""
    t = now.astimezone(datetime.UTC) - product.delay
    return t.replace(minute=t.minute - t.minute % 5, second=0, microsecond=0)


def day_of(slot: datetime.datetime) -> str:
    """Return the id of the daily item holding the image for slot."""
    return f"{slot.astimezone(datetime.UTC):%Y%m%d}-ch"


def stem_of(product: RadarProduct, slot: datetime.datetime) -> str:
    """Return the start of the file name of the image for slot."""
    t = slot.astimezone(datetime.UTC)
    return product.stem.format(t=t, doy=t.timetuple().tm_yday)


def radar_url(product: RadarProduct, slot: datetime.datetime, variant: str) -> str:
    """Return the URL of the image for the interval ending at slot."""
    return BASE_URL.format(
        collection=product.collection,
        day=day_of(slot),
        name=stem_of(product, slot) + variant + product.ext,
    )


def find_in_item(
    product: RadarProduct,
    slot: datetime.datetime,
    assets: dict[str, typing.Any],
) -> tuple[str, str] | None:
    """Return (variant, href) of the image for slot in a daily item's assets.

    Where an interval was published twice, the later file wins.
    """
    stem = stem_of(product, slot)
    found = sorted(
        (asset.get("created", ""), name[len(stem) : -len(product.ext)], asset["href"])
        for name, asset in assets.items()
        if name.startswith(stem) and name.endswith(product.ext)
    )
    if not found:
        return None
    return found[-1][1], found[-1][2]


def newest_variant(
    product: RadarProduct,
    slot: datetime.datetime,
    assets: dict[str, typing.Any],
) -> str | None:
    """Return the variant of the newest image of product in a daily item.

    A variant holds for hours, so it is the best guess for an image that
    is not out yet.
    """
    # Every stem of a product has the same length; only its prefix is fixed.
    length = len(stem_of(product, slot))
    prefix = product.stem.split("{", 1)[0]
    names = sorted(
        (asset.get("created", ""), name)
        for name, asset in assets.items()
        if name.startswith(prefix) and name.endswith(product.ext)
    )
    if not names:
        return None
    return names[-1][1][length : -len(product.ext)]


def read_pixel(content: bytes, lat: float, lon: float) -> float | None:
    """Return the value at lat/lon from a radar image.

    None means the radar has no data for that pixel.  The grid is read
    from the file, so a change of grid does not silently shift the pixel.
    """
    import pyfive

    f = pyfive.File(io.BytesIO(content))
    where = f["where"].attrs
    x_scale = float(where["xscale"])
    y_scale = float(where["yscale"])
    # Snap the upper-left corner to the grid; the formula is off by metres.
    left, top = wgs84_to_lv95(float(where["UL_lat"]), float(where["UL_lon"]))
    left = round(left / x_scale) * x_scale
    top = round(top / y_scale) * y_scale

    east, north = wgs84_to_lv95(lat, lon)
    col = math.floor((east - left) / x_scale)
    row = math.floor((top - north) / y_scale)
    if not (0 <= col < int(where["xsize"]) and 0 <= row < int(where["ysize"])):
        raise ValueError(
            f"{lat}, {lon} is outside the MeteoSwiss radar composite",
        )

    value = float(f["dataset1/data1/data"][row, col])
    if math.isnan(value):
        return None
    return value


@dataclass(frozen=True)
class RadarReading:
    """One radar reading at the configured location."""

    time: datetime.datetime  # end of the 5-minute interval, UTC
    value: float | None  # None where the radar has no data


class MeteoSwissRadarCoordinator(DataUpdateCoordinator[dict[str, RadarReading]]):
    """Fetch each new radar image once and read one pixel from it.

    The data holds a fresh reading per product.  Products are tracked
    separately, so a late or failed image of one product does not take
    the others down with it.
    """

    def __init__(self, hass: HomeAssistant, lat: float, lon: float) -> None:
        """Initialize."""
        self.lat = lat
        self.lon = lon
        # The variant each product's last image was found under.
        self._variants = {key: product.variant for key, product in PRODUCTS.items()}
        # (product, slot) pairs already looked up in the index, so an image
        # that is simply late costs one index download, not one per poll.
        self._looked_up: set[tuple[str, datetime.datetime]] = set()
        # Daily items fetched during the current update, shared by the
        # products of one collection.
        self._items: dict[tuple[str, str], asyncio.Task[dict[str, typing.Any]]] = {}
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} radar",
            update_interval=POLL_INTERVAL,
        )

    async def _fetch(self, url: str) -> bytes | None:
        """Download one file, or None if it does not exist (yet)."""
        session = async_get_clientsession(self.hass)
        async with asyncio.timeout(15):
            async with session.get(url, headers={"User-Agent": USER_AGENT}) as resp:
                # The file store answers 403, not 404, for a missing file.
                if resp.status in (403, 404):
                    return None
                resp.raise_for_status()
                return await resp.read()

    async def _item_assets(self, collection: str, day: str) -> dict[str, typing.Any]:
        """Return the assets of a daily item, fetched once per update."""
        key = (collection, day)
        if key not in self._items:

            async def fetch() -> dict[str, typing.Any]:
                content = await self._fetch(
                    ITEM_URL.format(collection=collection, day=day)
                )
                return json.loads(content)["assets"] if content else {}

            self._items[key] = asyncio.ensure_future(fetch())
        return await self._items[key]

    async def _fetch_image(
        self,
        key: str,
        product: RadarProduct,
        slot: datetime.datetime,
        now: datetime.datetime,
    ) -> bytes | None:
        """Download the image for slot, or None if it is not out (yet)."""
        tried = []
        for variant in dict.fromkeys((self._variants[key], product.variant)):
            tried.append(variant)
            content = await self._fetch(radar_url(product, slot, variant))
            if content is not None:
                self._variants[key] = variant
                return content

        # Not under the usual names.  Once it is overdue, ask the index -
        # the listing is ~300 kB by the end of the day, so only then.
        overdue = now - slot > product.delay + OVERDUE
        if not overdue or (key, slot) in self._looked_up:
            return None
        self._looked_up.add((key, slot))
        assets = await self._item_assets(product.collection, day_of(slot))
        found = find_in_item(product, slot, assets)
        if found is None:
            # Late as well as renamed: a variant that comes with a longer
            # delay can keep every image out of the index when it is read.
            # Learn the name from the newest image instead, so the next
            # poll asks for the right file.
            variant = newest_variant(product, slot, assets)
            if variant is not None and variant != self._variants[key]:
                _LOGGER.debug("Radar %s is now published as variant %s", key, variant)
                self._variants[key] = variant
            return None
        variant, href = found
        _LOGGER.debug("Radar %s %s is published as variant %s", key, slot, variant)
        self._variants[key] = variant
        return await self._fetch(href)

    async def _update_product(
        self,
        key: str,
        current: RadarReading | None,
        now: datetime.datetime,
    ) -> RadarReading | None:
        """Return the newest reading of one product, or None if none is fresh."""
        product = PRODUCTS[key]
        newest = latest_slot(product, now)
        if current is not None and current.time >= newest:
            return current

        # A reading still inside MAX_AGE survives a late image or a failed
        # download; only a stale one is dropped.
        fresh = current if current and now - current.time < MAX_AGE else None
        for slot in (newest, newest - SLOT):
            if current is not None and slot <= current.time:
                break
            try:
                content = await self._fetch_image(key, product, slot, now)
                if content is None:
                    continue
                value = await self.hass.async_add_executor_job(
                    read_pixel,
                    content,
                    self.lat,
                    self.lon,
                )
            except (TimeoutError, aiohttp.ClientError) as exc:
                if fresh is None:
                    raise UpdateFailed(f"Cannot fetch radar {key}: {exc}") from exc
                _LOGGER.debug("Cannot fetch radar %s: %s", key, exc)
                return fresh
            except Exception as exc:
                raise UpdateFailed(f"Cannot read radar {key}: {exc}") from exc
            if value is not None:
                value = round(value * product.scale, 2)
            return RadarReading(time=slot, value=value)
        return fresh

    async def _async_update_data(self) -> dict[str, RadarReading]:
        """Return a fresh reading per product, downloading only new images."""
        now = dt_util.utcnow()
        previous = self.data or {}
        keys = list(PRODUCTS)
        self._items = {}
        self._looked_up = {
            (key, slot) for key, slot in self._looked_up if now - slot < MAX_AGE
        }
        results = await asyncio.gather(
            *(self._update_product(key, previous.get(key), now) for key in keys),
            return_exceptions=True,
        )

        data: dict[str, RadarReading] = {}
        errors: list[BaseException] = []
        for key, result in zip(keys, results):
            if isinstance(result, BaseException):
                _LOGGER.debug("Radar %s: %s", key, result)
                errors.append(result)
            elif result is not None:
                data[key] = result
        if not data:
            if errors:
                raise UpdateFailed(str(errors[0]))
            raise UpdateFailed("No fresh radar image for any product")
        return data
