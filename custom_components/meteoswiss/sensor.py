import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Union

from hamsclientfork.client import StationType
from homeassistant.components.sensor import (
    SensorEntity, 
    SensorStateClass,
    SensorDeviceClass
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.meteoswiss import MeteoSwissDataUpdateCoordinator
from custom_components.meteoswiss.const import (
    CONF_POSTCODE,
    CONF_PRECIPITATION_STATION,
    CONF_REAL_TIME_NAME,
    CONF_REAL_TIME_PRECIPITATION_NAME,
    CONF_STATION,
    DOMAIN,
    SENSOR_DATA_ID,
    SENSOR_TYPE_CLASS,
    SENSOR_TYPE_ICON,
    SENSOR_TYPE_NAME,
    SENSOR_TYPE_UNIT,
    SENSOR_TYPES,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up all sensors."""
    _LOGGER.debug("Starting async setup platform for sensor")
    coordinator: MeteoSwissDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []

    # Sensoren für Wetterstation
    if coordinator.weather_station:
        entities.extend([
            MeteoSwissSensor(entry.entry_id, typ, coordinator, StationType.WEATHER)
            for typ in SENSOR_TYPES
        ])
    else:
        _LOGGER.debug("Keine Wetterstation konfiguriert - überspringe Wetter-Sensoren.")

    # Sensoren für Niederschlagsstation
    if coordinator.precipitation_station:
        entities.extend([
            MeteoSwissSensor(entry.entry_id, typ, coordinator, StationType.PRECIPITATION)
            for typ in SENSOR_TYPES
        ])
    else:
        _LOGGER.debug("Keine Niederschlagsstation konfiguriert - überspringe Niederschlags-Sensoren.")

    if entities:
        async_add_entities(entities, True)


class MeteoSwissSensor(CoordinatorEntity[MeteoSwissDataUpdateCoordinator], SensorEntity):
    """Represents a sensor from MeteoSwiss."""

    def __init__(
        self,
        integration_id: str,
        sensor_type: str,
        coordinator: MeteoSwissDataUpdateCoordinator,
        station_type: StationType,
    ):
        super().__init__(coordinator)
        self._type = sensor_type
        self._station_type = station_type
        
        # Bestimme die Station-ID (Wetter oder Niederschlag)
        self._station_id = coordinator.data.get(
            CONF_STATION if station_type == StationType.WEATHER else CONF_PRECIPITATION_STATION
        )

        # Eindeutige ID generieren
        suffix = "-precipitation" if station_type == StationType.PRECIPITATION else ""
        self._attr_unique_id = f"sensor.{integration_id}-{sensor_type}{suffix}"
        
        # Sensor-Eigenschaften aus den Konstanten laden
        self._attr_native_unit_of_measurement = SENSOR_TYPES[self._type].get(SENSOR_TYPE_UNIT)
        self._attr_icon = SENSOR_TYPES[self._type].get(SENSOR_TYPE_ICON)
        self._attr_device_class = SENSOR_TYPES[self._type].get(SENSOR_TYPE_CLASS)
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def name(self) -> str:
        """Name des Sensors dynamisch generieren."""
        sensor_name_part = SENSOR_TYPES[self._type][SENSOR_TYPE_NAME]
        name_key = (
            CONF_REAL_TIME_NAME
            if self._station_type == StationType.WEATHER
            else CONF_REAL_TIME_PRECIPITATION_NAME
        )
        station_name = self.coordinator.data.get(name_key, "MeteoSwiss")
        return f"{station_name} {sensor_name_part}"

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        """Gibt den aktuellen Wert des Sensors zurück."""
        data_id = SENSOR_TYPES[self._type][SENSOR_DATA_ID]
        
        try:
            # Sicherer Zugriff auf die tief verschachtelten Daten
            station_data = self.coordinator.data.get("condition_by_station", {}).get(self._station_id)
            if station_data:
                return station_data.get(data_id)
        except Exception as e:
            _LOGGER.warning("Fehler beim Abrufen der Daten für %s: %s", self.name, e)
        
        return None

    @property
    def available(self) -> bool:
        """Prüft, ob der Sensor Daten liefert."""
        if not self.coordinator.last_update_success or not self.coordinator.data:
            return False
            
        data_id = SENSOR_TYPES[self._type][SENSOR_DATA_ID]
        station_data = self.coordinator.data.get("condition_by_station", {}).get(self._station_id)
        
        # Sensor ist verfügbar, wenn die Station existiert und die spezifische Daten-ID vorhanden ist
        return station_data is not None and data_id in station_data

    @callback
    def _handle_coordinator_update(self) -> None:
        """Wird aufgerufen, wenn der Coordinator neue Daten hat."""
        self.async_write_ha_state()
