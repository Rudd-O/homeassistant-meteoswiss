"""Lifecycle of MeteoSwiss."""

import datetime
import logging
import time
from typing import Literal, cast

from async_timeout import timeout
from hamsclientfork import meteoSwissClient
from hamsclientfork.client import ClientResult
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.issue_registry import IssueSeverity
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from custom_components.meteoswiss.const import (
    CONF_FORECAST_NAME,
    CONF_NAME,
    CONF_POSTCODE,
    CONF_PRECIPITATION_STATION,
    CONF_REAL_TIME_NAME,
    CONF_REAL_TIME_PRECIPITATION_NAME,
    CONF_STATION,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR, Platform.WEATHER]
MAX_CONTINUOUS_ERROR_TIME = 60 * 60


async def async_setup(hass: HomeAssistant, config: ConfigType) -> Literal[True]:
    """Setup via old entry in configuration.yaml."""
    _LOGGER.debug("Async setup: meteoswiss")

    conf = config.get(DOMAIN)
    if conf is None:
        return True

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data=conf
        )
    )
    _LOGGER.debug("END Async setup: meteoswiss")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    _LOGGER.debug("Current configuration: %s", entry.data)
    name = entry.data.get(
        CONF_FORECAST_NAME,
        entry.data.get(
            CONF_REAL_TIME_NAME,
            entry.data.get(CONF_NAME, ""),
        ),
    )
    if not name:
        entry_id = entry.entry_id
        ir.async_create_issue(
            hass,
            DOMAIN,
            f"{entry_id}_improperly_configured_{DOMAIN}",
            is_fixable=False,
            is_persistent=False,
            severity=IssueSeverity.ERROR,
            translation_key="improperly_configured",
            translation_placeholders={
                "entry_id": entry_id,
            },
        )
        return False

    interval = datetime.timedelta(
        seconds=entry.data.get(
            CONF_UPDATE_INTERVAL,
            DEFAULT_UPDATE_INTERVAL,
        )
        * 60
    )
    coordinator = MeteoSwissDataUpdateCoordinator(
        hass,
        interval,
        entry.data[CONF_POSTCODE],
        forecast_name=entry.data.get(CONF_FORECAST_NAME, name),
        weather_station=entry.data.get(CONF_STATION, None),
        real_time_weather_station_name=entry.data.get(CONF_REAL_TIME_NAME, None),
        precipitation_station=entry.data.get(CONF_PRECIPITATION_STATION, None),
        real_time_precipitation_station_name=entry.data.get(
            CONF_REAL_TIME_PRECIPITATION_NAME, None
        ),
    )
    await coordinator.async_config_entry_first_refresh()

    entry.async_on_unload(entry.add_update_listener(update_listener))

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class MeteoSwissClientResult(ClientResult):
    # Forecast attributes.
    postcode: int  # e.g. 8005
    forecast_name: str
    # Real-time weather station attributes.
    station: str | None  # e.g. BLA
    real_time_name: str | None
    # Real-time precipitation station attributes.
    precipitation_station: str | None  # e.g. BEL
    real_time_precipitation_name: str | None


class MeteoSwissDataUpdateCoordinator(DataUpdateCoordinator[MeteoSwissClientResult]):
    """Class to manage fetching MeteoSwiss data API."""

    data: MeteoSwissClientResult

    def __init__(
        self,
        hass: HomeAssistant,
        update_interval: datetime.timedelta,
        postcode: int,
        forecast_name: str,
        weather_station: str | None,
        real_time_weather_station_name: str | None,
        precipitation_station: str | None,
        real_time_precipitation_station_name: str | None,
    ) -> None:
        """Initialize."""
        self.first_error: dict[str, float | None] = {
            CONF_REAL_TIME_NAME: None,
            CONF_REAL_TIME_PRECIPITATION_NAME: None,
            CONF_POSTCODE: None,
        }
        self.error_raised = {
            CONF_REAL_TIME_NAME: False,
            CONF_REAL_TIME_PRECIPITATION_NAME: False,
            CONF_POSTCODE: False,
        }
        self.hass = hass
        self.postcode = postcode
        self.forecast_name = forecast_name
        _LOGGER.debug(
            "Forecast %s will be provided for post code %s every %s",
            forecast_name,
            postcode,
            update_interval,
        )

        self.weather_station = weather_station
        self.real_time_weather_station_name = real_time_weather_station_name
        if weather_station:
            _LOGGER.debug(
                "Real-time weather %s will be updated from %s every %s",
                real_time_weather_station_name,
                weather_station,
                update_interval,
            )

        self.precipitation_station = precipitation_station
        self.real_time_precipitation_station_name = real_time_precipitation_station_name
        if precipitation_station:
            _LOGGER.debug(
                "Real-time precipitation %s will be updated from %s every %s",
                real_time_precipitation_station_name,
                precipitation_station,
                update_interval,
            )

        self.client = meteoSwissClient(  # type:ignore[no-untyped-call]
            "%s / %s / %s"
            % (
                forecast_name,
                real_time_weather_station_name,
                real_time_precipitation_station_name,
            ),
            postcode,
            weather_station if weather_station else "NO STATION",
            precipitation_station if precipitation_station else "NO STATION",
        )
        _LOGGER.debug("Client obtained")

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> MeteoSwissClientResult:
        """Update data via library."""
        try:
            async with timeout(15):
                data = await self.hass.async_add_executor_job(
                    self.client.get_typed_data,
                )
        except Exception as exc:
            _LOGGER.exception("Failed getting data")
            raise UpdateFailed(exc) from exc

        # _LOGGER.debug("Data obtained (%s):\n%s", type(data), pprint.pformat(data))
        for station, name in (
            (self.weather_station, CONF_REAL_TIME_NAME),
            (
                self.precipitation_station,
                CONF_REAL_TIME_PRECIPITATION_NAME,
            ),
        ):
            if station:
                if not data["condition_by_station"].get(station):
                    # Oh no.  We could not retrieve the URL.
                    # We try 20 times.  If it does not succeed,
                    # we will induce a config error.
                    _LOGGER.warning(
                        "Station %s (%s) provided us with no real-time data",
                        station,
                        name,
                    )
                    if self.first_error[name] is None:
                        self.first_error[name] = time.time()

                    m = MAX_CONTINUOUS_ERROR_TIME
                    last_error: float = time.time() - cast(
                        float, self.first_error[name]
                    )
                    if not self.error_raised and last_error > m:
                        ir.async_create_issue(
                            self.hass,
                            DOMAIN,
                            f"{station}_{name}_provides_no_data_{DOMAIN}",
                            is_fixable=False,
                            is_persistent=False,
                            severity=IssueSeverity.ERROR,
                            translation_key="station_no_data",
                            translation_placeholders={
                                "station": station,
                            },
                        )
                        self.error_raised[name] = True
                else:
                    if self.error_raised[name]:
                        ir.async_delete_issue(
                            self.hass,
                            DOMAIN,
                            f"{station}_{name}_provides_no_data_{DOMAIN}",
                        )
                    self.first_error[name] = None
                    self.error_raised[name] = False

        if not data["forecast"]:
            # Oh no.  The forecast is empty.
            _LOGGER.warning(
                "Post code %s provided us with no forecast",
                self.postcode,
            )
            if self.first_error[CONF_POSTCODE] is None:
                self.first_error[CONF_POSTCODE] = time.time()

            m = MAX_CONTINUOUS_ERROR_TIME
            last_error: float = time.time() - cast(
                float, self.first_error[CONF_POSTCODE]
            )
            if not self.error_raised and last_error > m:
                ir.async_create_issue(
                    self.hass,
                    DOMAIN,
                    f"{self.postcode}_provides_no_forecast_{DOMAIN}",
                    is_fixable=False,
                    is_persistent=False,
                    severity=IssueSeverity.ERROR,
                    translation_key="postcode_no_data",
                    translation_placeholders={
                        "postcode": str(self.postcode),
                    },
                )
                self.error_raised[CONF_POSTCODE] = True
        else:
            if self.error_raised[CONF_POSTCODE]:
                ir.async_delete_issue(
                    self.hass,
                    DOMAIN,
                    f"{self.postcode}_provides_no_forecast_{DOMAIN}",
                )
            self.first_error[CONF_POSTCODE] = None
            self.error_raised[CONF_POSTCODE] = False

        newdata = cast(MeteoSwissClientResult, data)
        newdata[CONF_POSTCODE] = self.postcode
        newdata[CONF_FORECAST_NAME] = self.forecast_name
        newdata[CONF_STATION] = self.weather_station
        newdata[CONF_REAL_TIME_NAME] = self.real_time_weather_station_name
        newdata[CONF_PRECIPITATION_STATION] = self.precipitation_station
        newdata[CONF_REAL_TIME_PRECIPITATION_NAME] = (
            self.real_time_precipitation_station_name
        )
        import pprint

        _LOGGER.debug("Returning data: %s", pprint.pformat(newdata))
        return newdata
