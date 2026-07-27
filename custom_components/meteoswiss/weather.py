"""Support for the MeteoSwiss service."""

from __future__ import annotations

import datetime
import logging
import pprint
from typing import Any, cast

from hamsclientfork.client import CurrentCondition
from homeassistant.components.weather import (
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_NATIVE_PRECIPITATION,
    ATTR_FORECAST_NATIVE_TEMP,
    ATTR_FORECAST_NATIVE_TEMP_LOW,
    ATTR_FORECAST_TIME,
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_UNAVAILABLE,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.meteoswiss import (
    MeteoSwissClientResult,
    MeteoSwissDataUpdateCoordinator,
)
from custom_components.meteoswiss.const import (
    CODE_TO_CONDITION_MAP,
    CONF_FORECAST_NAME,
    CONF_POSTCODE,
    CONF_PRECIPITATION_STATION,
    CONF_REAL_TIME_NAME,
    CONF_REAL_TIME_PRECIPITATION_NAME,
    CONF_STATION,
    DOMAIN,
    STATION_URL,
)

_LOGGER = logging.getLogger(__name__)

INVALID_FORECAST_VALUE = 32767


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up weather entity."""
    c: MeteoSwissDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MeteoSwissWeather(entry.entry_id, c)], True)


def condition_name_to_first_value(
    condition: None | list[CurrentCondition], name: str
) -> float | None:
    if not condition:
        # Real-time weather station provides no data.
        _LOGGER.debug("Current condition is empty for all stations: %s", condition)
        return None
    for n, row in enumerate(condition):
        try:
            value = row[name]  # type:ignore[literal-required]
        except Exception:
            _LOGGER.exception(
                "Current condition %s (%s) has no value for %s", n, row, name
            )
            continue
        if value is None or value == "-":
            _LOGGER.debug(
                "Value %s of current condition %s (%s) is %s, so not available",
                name,
                n,
                row,
                value,
            )
            continue
        try:
            return float(value)
        except Exception:
            _LOGGER.exception(
                "Error converting %s to float for condition in row %s (%s)",
                value,
                n,
                row,
            )
            continue
    return None


class MeteoSwissWeather(
    CoordinatorEntity[MeteoSwissDataUpdateCoordinator],
    WeatherEntity,
):
    _attr_has_entity_name = True
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_pressure_unit = UnitOfPressure.HPA
    _attr_native_wind_speed_unit = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_supported_features = (
        WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_HOURLY
    )

    def __init__(
        self,
        integration_id: str,
        coordinator: MeteoSwissDataUpdateCoordinator,
    ):
        super().__init__(coordinator)
        self._invalid_legacy_icon_logged = False
        self._attr_unique_id = "weather.%s" % integration_id
        self._attr_postcode = coordinator.data[CONF_POSTCODE]
        self._attr_station = coordinator.data[CONF_STATION]
        self._attr_weather_station = self._attr_station
        self._attr_weather_station_name = coordinator.data[CONF_REAL_TIME_NAME]
        self._attr_precipitation_station = coordinator.data[CONF_PRECIPITATION_STATION]
        self._attr_precipitation_station_name = coordinator.data[
            CONF_REAL_TIME_PRECIPITATION_NAME
        ]

        a = "Data provided by MeteoSwiss."
        a += "  Forecasts from postal code %s." % (self._attr_postcode,)
        if self._attr_weather_station:
            a += "  Real-time weather data from weather station %s (%s)." % (
                self._attr_weather_station,
                self._attr_weather_station_name,
            )
        if self._attr_precipitation_station:
            a += "  Real-time precipitation data from weather station %s (%s)." % (
                self._attr_precipitation_station,
                self._attr_precipitation_station_name,
            )
        if self._attr_weather_station or self._attr_precipitation_station:
            url = STATION_URL
            a += "  Stations available at %s ." % (url,)
        else:
            a += "  No real-time stations used by this weather entry."
        self._attr_attribution = a

        self.__set_data(coordinator.data)

    def __set_data(self, data: MeteoSwissClientResult) -> None:
        self._displayName = data[CONF_FORECAST_NAME]
        self._forecastData = data["forecast"]
        self._condition_for_all_stations = data["condition"]

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle data update."""
        data = self.coordinator.data
        self.__set_data(data)
        self.async_write_ha_state()

    @property
    def name(self) -> Any:
        return self._displayName

    @property
    def native_temperature(self) -> float | None:
        return condition_name_to_first_value(
            self._condition_for_all_stations, "tre200s0"
        )

    @property
    def native_pressure(self) -> float | None:
        return condition_name_to_first_value(
            self._condition_for_all_stations, "prestas0"
        )

    @property
    def pressure_qff(self) -> float | None:
        return condition_name_to_first_value(
            self._condition_for_all_stations, "pp0qffs0"
        )

    @property
    def pressure_qnh(self) -> float | None:
        return condition_name_to_first_value(
            self._condition_for_all_stations, "pp0qnhs0"
        )

    @property
    def humidity(self) -> float | None:
        return condition_name_to_first_value(
            self._condition_for_all_stations, "ure200s0"
        )

    @property
    def native_wind_speed(self) -> float | None:
        return condition_name_to_first_value(
            self._condition_for_all_stations, "fu3010z0"
        )

    @property
    def wind_bearing(self) -> float | None:
        return condition_name_to_first_value(
            self._condition_for_all_stations, "dkl010z0"
        )

    # FIXME add precipitation conditions above.

    @property
    def condition(self) -> str | None:
        current_weather = self._forecastData["currentWeather"]
        symbolId = current_weather.get("icon")
        if symbolId in (None, INVALID_FORECAST_VALUE):
            replacement = current_weather.get("iconV2")
            if not self._invalid_legacy_icon_logged:
                _LOGGER.warning(
                    "MeteoSwiss returned invalid legacy current-weather icon %r; "
                    "using iconV2 %r",
                    symbolId,
                    replacement,
                )
                self._invalid_legacy_icon_logged = True
            symbolId = replacement
        else:
            self._invalid_legacy_icon_logged = False
        try:
            cond: str | None = (
                str(CODE_TO_CONDITION_MAP.get(symbolId, ("", None))[0]) or None
            )
            if cond is None:
                _LOGGER.error(
                    "MeteoSwiss returned no recognized current-weather icon: %r",
                    symbolId,
                )
                return STATE_UNAVAILABLE
            _LOGGER.debug(
                "Current symbol is %s, condition is: %s",
                symbolId,
                cond,
            )
            return cond
        except TypeError as exc:
            _LOGGER.error(
                "Expected an int, not %r, to decide on the forecast icon: %s",
                symbolId,
                exc,
            )
            _LOGGER.error("Forecast data: %r", self._forecastData)
            return STATE_UNAVAILABLE

    def _daily_forecast(self) -> list[Forecast] | None:
        if not self._forecastData:
            return None
        fcdata_out: list[Forecast] = []
        # Skip the first element - it's the forecast for the current day
        try:
            for forecast in self._forecastData["regionForecast"]:
                data_out: Forecast = {
                    ATTR_FORECAST_TIME: forecast["dayDate"],
                    ATTR_FORECAST_NATIVE_TEMP_LOW: forecast["temperatureMin"],
                    ATTR_FORECAST_NATIVE_TEMP: forecast["temperatureMax"],
                    ATTR_FORECAST_CONDITION: str(
                        CODE_TO_CONDITION_MAP.get(forecast["iconDay"], ("", None))[0]
                    )
                    or None,
                    ATTR_FORECAST_NATIVE_PRECIPITATION: forecast["precipitation"],
                }
                fcdata_out.append(data_out)
        except Exception as e:
            _LOGGER.exception(
                "Error while converting daily forecast: %s\nForecast data: %s",
                e,
                pprint.pformat(self._forecastData["regionForecast"]),
            )
            raise
        _LOGGER.debug("Daily forecast has %d items", len(fcdata_out))
        return fcdata_out

    def _hourly_forecast(self) -> list[Forecast] | None:
        if not self._forecastData:
            return None
        fcdata_out: list[Forecast] = []
        # Skip the first element - it's the forecast for the current day
        now = datetime.datetime.now(datetime.timezone.utc)
        forecast_data = self._forecastData["regionHourlyForecast"]
        biggers = [f["time"] > now for f in forecast_data]
        try:
            idx = biggers.index(True)
        except IndexError:
            return fcdata_out
        try:
            for forecast in forecast_data[idx - 1 :]:
                data_out: Forecast = {
                    ATTR_FORECAST_TIME: forecast["time"]
                    .isoformat("T")
                    .partition("+")[0]
                    + "Z",
                    ATTR_FORECAST_NATIVE_TEMP_LOW: forecast["temperatureMin"],
                    ATTR_FORECAST_NATIVE_TEMP: forecast["temperatureMax"],
                    ATTR_FORECAST_NATIVE_PRECIPITATION: forecast["precipitationMax"],
                }
                fcdata_out.append(data_out)
        except Exception as e:
            _LOGGER.exception(
                "Error while converting hourly forecast: %s\nForecast data: %s",
                e,
                pprint.pformat(self._forecastData["regionHourlyForecast"]),
            )
            raise
        _LOGGER.debug("Hourly forecast has %d items", len(fcdata_out))
        return fcdata_out

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return bool(self._daily_forecast())

    async def async_forecast_daily(self) -> list[Forecast]:
        """Return the daily forecast in native units."""
        return self._daily_forecast() or []

    async def async_forecast_hourly(self) -> list[Forecast]:
        """Return the hourly forecast in native units."""
        return self._hourly_forecast() or []
