"""Support for the MeteoSwiss service."""

from __future__ import annotations

import datetime
import logging
from typing import Any, cast

from hamsclientfork.client import CurrentCondition, DayForecast, HourlyForecast
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
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import MeteoSwissDataUpdateCoordinator
from .const import (
    CODE_TO_CONDITION_MAP,
    CONF_FORECAST_NAME,
    CONF_POSTCODE,
    CONF_PRECIPITATION_STATION,
    CONF_REAL_TIME_NAME,
    CONF_REAL_TIME_PRECIPITATION_NAME,
    CONF_STATION,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up weather entity."""
    coordinator: MeteoSwissDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MeteoSwissWeather(entry.entry_id, coordinator)], True)

def condition_name_to_first_value(
    condition: list[CurrentCondition] | None, name: str
) -> float | None:
    """Extracts a numeric value from the list of station conditions."""
    if not condition:
        return None
    
    for row in condition:
        value = row.get(name)
        if value is None or value == "-":
            continue
        try:
            return float(value)
        except (ValueError, TypeError):
            continue
    return None

class MeteoSwissWeather(
    CoordinatorEntity[MeteoSwissDataUpdateCoordinator],
    WeatherEntity,
):
    """Implementation of a MeteoSwiss weather entity."""

    _attr_has_entity_name = True
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_pressure_unit = UnitOfPressure.HPA
    _attr_native_wind_speed_unit = UnitOfSpeed.KILOMETERS_PER_HOUR
    
    # Aktiviert die Unterstützung für moderne Forecast-Abfragen
    _attr_supported_features = (
        WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_HOURLY
    )

    def __init__(
        self,
        integration_id: str,
        coordinator: MeteoSwissDataUpdateCoordinator,
    ):
        super().__init__(coordinator)
        self._attr_unique_id = f"weather_{integration_id}"
        self._attr_name = coordinator.data.get(CONF_FORECAST_NAME, "MeteoSwiss")
        
        # Metadata für Attribution
        self._post_code = coordinator.data[CONF_POSTCODE]
        self._station = coordinator.data.get(CONF_STATION)
        self._station_name = coordinator.data.get(CONF_REAL_TIME_NAME)
        self._precip_station = coordinator.data.get(CONF_PRECIPITATION_STATION)
        self._precip_station_name = coordinator.data.get(CONF_REAL_TIME_PRECIPITATION_NAME)

    @property
    def native_temperature(self) -> float | None:
        return condition_name_to_first_value(self.coordinator.data.get("condition"), "tre200s0")

    @property
    def native_pressure(self) -> float | None:
        return condition_name_to_first_value(self.coordinator.data.get("condition"), "prestas0")

    @property
    def humidity(self) -> float | None:
        return condition_name_to_first_value(self.coordinator.data.get("condition"), "ure200s0")

    @property
    def native_wind_speed(self) -> float | None:
        return condition_name_to_first_value(self.coordinator.data.get("condition"), "fu3010z0")

    @property
    def wind_bearing(self) -> float | None:
        return condition_name_to_first_value(self.coordinator.data.get("condition"), "dkl010z0")

    @property
    def condition(self) -> str | None:
        """Return the current condition."""
        try:
            symbol_id = self.coordinator.data["forecast"]["currentWeather"]["icon"]
            return CODE_TO_CONDITION_MAP.get(symbol_id, (None, None))[0]
        except (KeyError, TypeError):
            return None

    @property
    def attribution(self) -> str:
        """Return the attribution with station info."""
        msg = f"Data by MeteoSwiss. Forecast for {self._post_code}."
        if self._station:
            msg += f" Real-time: {self._station_name} ({self._station})."
        return msg

    async def async_forecast_daily(self) -> list[Forecast]:
        """Modern method for daily forecast."""
        fc_data = self.coordinator.data.get("forecast", {}).get("regionForecast", [])
        forecasts: list[Forecast] = []
        
        for entry in fc_data:
            day = cast(DayForecast, entry)
            forecasts.append({
                ATTR_FORECAST_TIME: day["dayDate"],
                ATTR_FORECAST_NATIVE_TEMP: day["temperatureMax"],
                ATTR_FORECAST_NATIVE_TEMP_LOW: day["temperatureMin"],
                ATTR_FORECAST_NATIVE_PRECIPITATION: day["precipitation"],
                ATTR_FORECAST_CONDITION: CODE_TO_CONDITION_MAP.get(day["iconDay"], (None, None))[0],
            })
        return forecasts

    async def async_forecast_hourly(self) -> list[Forecast]:
        """Modern method for hourly forecast."""
        fc_data = self.coordinator.data.get("forecast", {}).get("regionHourlyForecast", [])
        forecasts: list[Forecast] = []
        now = datetime.datetime.now(datetime.timezone.utc)
        
        for entry in fc_data:
            hour = cast(HourlyForecast, entry)
            # Nur zukünftige Stunden anzeigen
            if hour["time"] < now - datetime.timedelta(hours=1):
                continue
                
            forecasts.append({
                ATTR_FORECAST_TIME: hour["time"].isoformat(),
                ATTR_FORECAST_NATIVE_TEMP: hour["temperatureMax"],
                ATTR_FORECAST_NATIVE_TEMP_LOW: hour["temperatureMin"],
                ATTR_FORECAST_NATIVE_PRECIPITATION: hour["precipitationMax"],
                # Hinweis: Hourly icons könnten anders gemappt sein, falls vorhanden
                ATTR_FORECAST_CONDITION: self.condition, 
            })
        return forecasts
