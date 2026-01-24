import logging
import re
from typing import Any

import voluptuous as vol
from hamsclientfork import StationType, meteoSwissClient
from homeassistant import config_entries
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.issue_registry import IssueSeverity

from custom_components.meteoswiss.const import (
    CONF_FORECAST_NAME,
    CONF_LAT,
    CONF_LON,
    CONF_NAME,
    CONF_POSTCODE,
    CONF_PRECIPITATION_NAME,
    CONF_PRECIPITATION_STATION,
    CONF_REAL_TIME_NAME,
    CONF_REAL_TIME_PRECIPITATION_NAME,
    CONF_STATION,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)

NO_STATION = "Keine Wetterstation"
NO_PRECIPITATION_STATION = "Keine Niederschlagsstation"

class MeteoSwissFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Init FlowHandler."""
        super().__init__()
        self._lat = None
        self._lon = None
        self._post_code = None
        self._forecast_name = None
        self._update_interval = None

    async def async_step_user(self, user_input=None):
        """Erster Schritt: Abfrage der Koordinaten."""
        errors = {}
        if user_input is not None:
            if not (-90 <= user_input[CONF_LAT] <= 90):
                errors[CONF_LAT] = "latitude_error"
            if not (-180 <= user_input[CONF_LON] <= 180):
                errors[CONF_LON] = "longitude_error"
            
            if not errors:
                self._lat = user_input[CONF_LAT]
                self._lon = user_input[CONF_LON]
                return await self.async_step_user_two()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_LAT, default=self.hass.config.latitude): float,
                vol.Required(CONF_LON, default=self.hass.config.longitude): float,
            }),
            errors=errors
        )

    async def async_step_user_two(self, user_input=None):
        """Zweiter Schritt: PLZ und Update-Intervall."""
        errors = {}
        
        if user_input is not None:
            # Validierung
            if not re.match(r"^\d{4}$", str(user_input[CONF_POSTCODE])):
                errors[CONF_POSTCODE] = "invalid_postcode"
            if user_input[CONF_UPDATE_INTERVAL] < 1:
                errors[CONF_UPDATE_INTERVAL] = "update_interval_too_low"
            
            if not errors:
                self._post_code = int(user_input[CONF_POSTCODE])
                self._forecast_name = user_input[CONF_FORECAST_NAME].strip()
                self._update_interval = int(user_input[CONF_UPDATE_INTERVAL])
                return await self.async_step_user_three()

        # Automatische Ermittlung der PLZ falls kein user_input vorliegt
        guessed_postal_code = ""
        guessed_address = ""
        
        try:
            client = await self.hass.async_add_executor_job(meteoSwissClient, "Temp", None)
            geodata = await self.hass.async_add_executor_job(
                client.getGeoData, self._lat, self._lon, USER_AGENT
            )
            guessed_postal_code = geodata.get("address", {}).get("postcode", "")
            guessed_address = geodata.get("display_name", "").split(",")[0]
        except Exception:
            _LOGGER.debug("Konnte Geodaten nicht automatisch ermitteln")

        return self.async_show_form(
            step_id="user_two",
            data_schema=vol.Schema({
                vol.Required(CONF_POSTCODE, default=guessed_postal_code): str,
                vol.Required(CONF_FORECAST_NAME, default=guessed_address): str,
                vol.Required(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): int,
            }),
            errors=errors
        )

    async def _get_stations_mapping(self, client, station_type: StationType):
        """Hilfsfunktion zum Laden der Stationen."""
        stations = await self.hass.async_add_executor_job(client.get_all_stations, station_type)
        closest = await self.hass.async_add_executor_job(
            client.get_closest_station, self._lat, self._lon, station_type
        )
        
        mapping = {NO_STATION if station_type == StationType.WEATHER else NO_PRECIPITATION_STATION: None}
        for code, info in stations.items():
            label = f"{info['name']} ({code})"
            mapping[label] = code
            
        # Finde den Label für die nächstgelegene Station
        default_label = next((l for l, c in mapping.items() if c == closest), list(mapping.keys())[0])
        return mapping, default_label

    async def async_step_user_three(self, user_input=None):
        """Dritter Schritt: Auswahl der Stationen."""
        errors = {}
        client = await self.hass.async_add_executor_job(meteoSwissClient, "Setup", self._post_code)
        
        weather_mapping, def_w_label = await self._get_stations_mapping(client, StationType.WEATHER)
        precip_mapping, def_p_label = await self._get_stations_mapping(client, StationType.PRECIPITATION)

        if user_input is not None:
            # Daten sammeln
            w_code = weather_mapping.get(user_input[CONF_STATION])
            p_code = precip_mapping.get(user_input[CONF_PRECIPITATION_STATION])
            
            data = {
                CONF_POSTCODE: self._post_code,
                CONF_FORECAST_NAME: self._forecast_name,
                CONF_UPDATE_INTERVAL: self._update_interval,
            }
            
            if w_code:
                data[CONF_STATION] = w_code
                data[CONF_REAL_TIME_NAME] = user_input[CONF_REAL_TIME_NAME]
            if p_code:
                data[CONF_PRECIPITATION_STATION] = p_code
                data[CONF_REAL_TIME_PRECIPITATION_NAME] = user_input[CONF_REAL_TIME_PRECIPITATION_NAME]

            return self.async_create_entry(title=self._forecast_name, data=data)

        return self.async_show_form(
            step_id="user_three",
            data_schema=vol.Schema({
                vol.Required(CONF_STATION, default=def_w_label): vol.In(list(weather_mapping.keys())),
                vol.Optional(CONF_REAL_TIME_NAME, default=self._forecast_name): str,
                vol.Required(CONF_PRECIPITATION_STATION, default=def_p_label): vol.In(list(precip_mapping.keys())),
                vol.Optional(CONF_REAL_TIME_PRECIPITATION_NAME, default=self._forecast_name): str,
            }),
            errors=errors
        )

    async def async_step_import(self, import_config: dict[str, Any]):
        """Import aus YAML (deprecated)."""
        ir.async_create_issue(
            self.hass, DOMAIN, "deprecated_yaml", is_fixable=False,
            severity=IssueSeverity.WARNING, translation_key="deprecated_yaml",
        )
        return self.async_create_entry(
            title=import_config.get(CONF_NAME, "MeteoSwiss Import"),
            data=import_config
        )
