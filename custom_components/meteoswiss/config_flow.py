"""Config flow to configure the Meteo-Swiss integration."""

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
    STATION_URL,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)


NO_STATION = "No real-time weather station"
NO_PRECIPITATION_STATION = "No real-time precipitation station"


class MeteoSwissFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):  # type:ignore
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
        """Handle a flow initiated by the user.

        In this step, we collect the latitude and longitude.
        """

        _LOGGER.debug(
            "step user: starting with lat %s lon %s post %s",
            self._lat,
            self._lon,
            self._post_code,
        )

        def data_schema(lat, lon):
            return vol.Schema(
                {
                    vol.Required(
                        CONF_LAT,
                        default=lat,
                    ): float,
                    vol.Required(
                        CONF_LON,
                        default=lon,
                    ): float,
                }
            )

        errors = {}
        if user_input is not None:
            if user_input[CONF_LAT] > 90 or user_input[CONF_LAT] < -90:
                errors["lat"] = "latitude_error"
            if user_input[CONF_LON] > 180 or user_input[CONF_LON] < -180:
                errors["lon"] = "longitude_error"
            schema = data_schema(user_input[CONF_LAT], user_input[CONF_LON])
        else:
            schema = data_schema(
                self.hass.config.latitude,
                self.hass.config.longitude,
            )

        if errors or user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=schema, errors=errors
            )

        self._lat = user_input[CONF_LAT]
        self._lon = user_input[CONF_LON]
        _LOGGER.debug(
            "step user: continuing with lat %s lon %s post %s",
            self._lat,
            self._lon,
            self._post_code,
        )
        return await self.async_step_user_two()

    async def async_step_user_two(self, user_input=None):
        """Handle the second step of setup.

        In this step we collect the postal code, the name of the forecast,
        and the update interval.
        """

        _LOGGER.debug(
            "step user two: starting with lat %s lon %s post %s",
            self._lat,
            self._lon,
            self._post_code,
        )

        def data_schema(postcode, name, interval):
            return vol.Schema(
                {
                    vol.Required(
                        CONF_POSTCODE,
                        default=postcode,
                    ): str,
                    vol.Required(
                        CONF_FORECAST_NAME,
                        default=name,
                    ): str,
                    vol.Required(
                        CONF_UPDATE_INTERVAL,
                        default=interval,
                    ): int,
                }
            )

        client = await self.hass.async_add_executor_job(
            meteoSwissClient,
            "No display name",
            user_input.get(CONF_POSTCODE) if user_input else None,
        )

        errors = {}
        if user_input is not None:
            if not re.match(r"^\d{4}$", str(user_input[CONF_POSTCODE])):
                errors[CONF_POSTCODE] = "invalid_postcode"
            if not str(user_input[CONF_FORECAST_NAME]).strip():
                errors[CONF_FORECAST_NAME] = "real_time_name_empty"
            # check if the station name is 3 character
            if user_input[CONF_UPDATE_INTERVAL] < 1:
                errors[CONF_UPDATE_INTERVAL] = "update_interval_too_low"

            schema = data_schema(
                user_input[CONF_POSTCODE],
                user_input[CONF_FORECAST_NAME],
                user_input[CONF_UPDATE_INTERVAL],
            )
        else:
            try:
                geodata = await self.hass.async_add_executor_job(
                    client.getGeoData,
                    self._lat,
                    self._lon,
                    USER_AGENT,
                )
                guessed_postal_code = str(
                    geodata.get("address", {}).get(
                        "postcode",
                        "",
                    )
                )
                guessed_address = " ".join(
                    x.strip()
                    for x in str(
                        geodata.get(
                            "display_name",
                            "",
                        )
                    ).split(",")[:3]
                )
            except Exception:
                errors[CONF_POSTCODE] = "cannot_query_postcode"
                errors[CONF_FORECAST_NAME] = "cannot_query_address"
                guessed_postal_code = ""
                guessed_address = ""

            schema = data_schema(
                guessed_postal_code,
                guessed_address,
                DEFAULT_UPDATE_INTERVAL,
            )

        if errors or user_input is None:
            return self.async_show_form(
                step_id="user_two", data_schema=schema, errors=errors
            )

        self._post_code = int(user_input[CONF_POSTCODE])
        self._forecast_name = user_input[CONF_FORECAST_NAME].strip()
        self._update_interval = int(user_input[CONF_UPDATE_INTERVAL])
        _LOGGER.debug(
            "step user two: continuing with lat %s lon %s post %s name %s",
            self._lat,
            self._lon,
            self._post_code,
            self._forecast_name,
        )
        return await self.async_step_user_three()

    async def _get_all_weather_stations_and_closest_one(
        self, client, lat, lon
    ) -> tuple[str, str, str]:
        return await self._get_all_stations_and_closest_one(
            client, lat, lon, station_type=StationType.WEATHER
        )

    async def _get_all_precipitation_stations_and_closest_one(
        self, client, lat, lon
    ) -> tuple[str, str, str]:
        return await self._get_all_stations_and_closest_one(
            client, lat, lon, station_type=StationType.PRECIPITATION
        )

    async def _get_all_stations_and_closest_one(
        self, client, lat, lon, station_type
    ) -> tuple[str, str, str]:
        default_station = await self.hass.async_add_executor_job(
            client.get_closest_station,
            lat,
            lon,
            station_type,
        )
        if default_station:
            default_station_name = await self.hass.async_add_executor_job(
                client.get_station_name, default_station
            )
        else:
            default_station_name = ""
        stations = await self.hass.async_add_executor_job(
            client.get_all_stations,
            station_type,
        )
        all_stations = {NO_STATION: ""}
        all_stations.update(
            {
                "%s (%s)"
                % (
                    value["name"],
                    key,
                ): key
                for key, value in stations.items()
            }
        )
        return default_station, default_station_name, all_stations

    async def async_step_user_three(self, user_input=None):
        """Handle the step of setup."""
        _LOGGER.debug(
            "step user three: continuing with lat %s lon %s post %s",
            self._lat,
            self._lon,
            self._post_code,
        )

        def data_schema(
            name,
            weather_station,
            weather_stations,
            precipitation_name,
            precipitation_station,
            precipitation_stations,
        ):
            return vol.Schema(
                {
                    vol.Required(
                        CONF_STATION,
                        default=weather_station,
                    ): vol.In(list(weather_stations)),
                    vol.Optional(
                        CONF_REAL_TIME_NAME,
                        default=name,
                    ): str,
                    vol.Required(
                        CONF_PRECIPITATION_STATION,
                        default=precipitation_station,
                    ): vol.In(list(precipitation_stations)),
                    vol.Optional(
                        CONF_REAL_TIME_PRECIPITATION_NAME,
                        default=precipitation_name,
                    ): str,
                }
            )

        client = await self.hass.async_add_executor_job(
            meteoSwissClient,
            "No display name",
            self._post_code,
        )

        (
            default_weather_station,
            default_weather_station_name,
            weather_stations,
        ) = await self._get_all_weather_stations_and_closest_one(
            client,
            self._lat,
            self._lon,
        )

        (
            default_precipitation_station,
            default_precipitation_station_name,
            precipitation_stations,
        ) = await self._get_all_precipitation_stations_and_closest_one(
            client,
            self._lat,
            self._lon,
        )

        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input[CONF_STATION] not in weather_stations:
                errors[CONF_STATION] = "invalid_station_name"
            weather_station = weather_stations[user_input[CONF_STATION]]
            if weather_station:
                real_time_weather_name = user_input[CONF_REAL_TIME_NAME].strip()
                if len(real_time_weather_name) < 1:
                    errors[CONF_REAL_TIME_NAME] = "empty_name"
                # check if the station name is 3 character
                if not re.match(r"^\w{3}$", weather_station):
                    errors[CONF_STATION] = "invalid_station_name"
            else:
                weather_station = None
                real_time_weather_name = None

            if user_input[CONF_PRECIPITATION_STATION] not in precipitation_stations:
                errors[CONF_PRECIPITATION_STATION] = "invalid_station_name"
            precipitation_station = precipitation_stations[
                user_input[CONF_PRECIPITATION_STATION]
            ]
            if precipitation_station:
                real_time_precipitation_name = user_input[
                    CONF_REAL_TIME_PRECIPITATION_NAME
                ].strip()
                if len(real_time_precipitation_name) < 1:
                    errors[CONF_REAL_TIME_PRECIPITATION_NAME] = "empty_name"
                # check if the station name is 3 character
                if not re.match(r"^\w{3}$", weather_station):
                    errors[CONF_PRECIPITATION_STATION] = "invalid_station_name"
            else:
                precipitation_station = None
                real_time_precipitation_name = None

            schema = data_schema(
                user_input[CONF_REAL_TIME_NAME],
                user_input[CONF_STATION],
                weather_stations,
                user_input[CONF_REAL_TIME_PRECIPITATION_NAME],
                user_input[CONF_PRECIPITATION_STATION],
                precipitation_stations,
            )
        else:
            if default_weather_station:
                default_station_selection = "%s (%s)" % (
                    default_weather_station_name,
                    default_weather_station,
                )
            else:
                default_weather_station = NO_PRECIPITATION_STATION
            if default_precipitation_station:
                default_precipitation_station_selection = "%s (%s)" % (
                    default_precipitation_station_name,
                    default_precipitation_station,
                )
            else:
                default_precipitation_station_selection = NO_PRECIPITATION_STATION
            default_weather_station_name = default_weather_station_name or ""
            default_precipitation_station_name = (
                default_precipitation_station_name or ""
            )

            schema = data_schema(
                default_weather_station_name,
                default_station_selection,
                weather_stations,
                default_precipitation_station_name,
                default_precipitation_station_selection,
                precipitation_stations,
            )

        if errors or user_input is None:
            return self.async_show_form(
                step_id="user_three",
                data_schema=schema,
                errors=errors,
                description_placeholders={
                    "station_url": STATION_URL,
                },
            )

        data = {
            CONF_POSTCODE: self._post_code,
            CONF_FORECAST_NAME: self._forecast_name,
            CONF_UPDATE_INTERVAL: self._update_interval,
        }
        if weather_station and real_time_weather_name:
            data.update(
                {
                    CONF_STATION: weather_station,
                    CONF_REAL_TIME_NAME: real_time_weather_name,
                }
            )
        if precipitation_station and real_time_precipitation_name:
            data.update(
                {
                    CONF_PRECIPITATION_STATION: precipitation_station,
                    CONF_REAL_TIME_PRECIPITATION_NAME: real_time_precipitation_name,
                }
            )

        title = self._forecast_name
        if real_time_weather_name:
            title += f" / {real_time_weather_name}"
        if real_time_precipitation_name:
            title += f" / {real_time_precipitation_name}"

        _LOGGER.debug(
            "step user three: finishing with %s",
            data,
        )
        return self.async_create_entry(
            title=title,
            data=data,
        )

    async def async_step_import(self, import_config: dict[str, Any]):
        """Import a config entry."""
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            "deprecated_yaml",
            is_fixable=False,
            severity=IssueSeverity.WARNING,
            translation_key="deprecated_yaml",
        )

        data = {
            CONF_POSTCODE: import_config[CONF_POSTCODE],
            CONF_UPDATE_INTERVAL: import_config.get(
                CONF_UPDATE_INTERVAL,
                DEFAULT_UPDATE_INTERVAL,
            ),
            CONF_FORECAST_NAME: import_config[CONF_NAME],
        }
        if import_config.get(CONF_STATION):
            data[CONF_STATION] = import_config[CONF_STATION]
            data[CONF_REAL_TIME_NAME] = import_config[CONF_NAME]
        if import_config.get(CONF_PRECIPITATION_STATION):
            data[CONF_PRECIPITATION_STATION] = import_config[CONF_PRECIPITATION_STATION]
            data[CONF_REAL_TIME_PRECIPITATION_NAME] = import_config[
                CONF_PRECIPITATION_NAME
            ]

        return self.async_create_entry(
            title=data[CONF_NAME],
            data=data,
        )
