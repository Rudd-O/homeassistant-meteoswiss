"""Constants for MeteoSwiss."""

from __future__ import annotations

from enum import StrEnum

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import (
    CONF_NAME,
    DEGREE,
    PERCENTAGE,
    UnitOfIrradiance,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolumetricFlux,
)

DOMAIN = "meteoswiss"

# Konfigurations-Schlüssel
CONF_PRECIPITATION_NAME = "precipitation_name"
CONF_FORECAST_NAME = "forecast_name"
CONF_POSTCODE = "postcode"
CONF_STATION = "station"
CONF_REAL_TIME_NAME = "real_time_name"
CONF_PRECIPITATION_STATION = "precipitation_station"
CONF_REAL_TIME_PRECIPITATION_NAME = "real_time_precipitation_name"
CONF_FORECASTTYPE = "forecasttype"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_LAT = "latitude"
CONF_LON = "longitude"

DEFAULT_UPDATE_INTERVAL = 5
USER_AGENT = "MeteoSwiss Home Assistant integration"

class Condition(StrEnum):
    """Wetterzustände für Home Assistant."""
    partly_cloudy = "partlycloudy"
    clear_night = "clear-night"
    cloudy = "cloudy"
    exceptional = "exceptional"
    fog = "fog"
    hail = "hail"
    lightning = "lightning"
    lightning_rainy = "lightning-rainy"
    pouring = "pouring"
    rainy = "rainy"
    snowy = "snowy"
    snowy_rainy = "snowy-rainy"
    sunny = "sunny"
    windy = "windy"
    windy_variant = "windy-variant"

# Mapping der MeteoSwiss Icon-IDs auf HA Conditions
CODE_TO_CONDITION_MAP = {
    1: (Condition.sunny, "sunny"),
    2: (Condition.partly_cloudy, "mostly sunny, some clouds"),
    3: (Condition.partly_cloudy, "partly sunny, thick passing clouds"),
    4: (Condition.partly_cloudy, "overcast"),
    5: (Condition.cloudy, "very cloudy"),
    6: (Condition.rainy, "sunny intervals, isolated showers"),
    7: (Condition.snowy_rainy, "sunny intervals, isolated sleet"),
    8: (Condition.snowy, "sunny intervals, snow showers"),
    9: (Condition.rainy, "overcast, some rain showers"),
    10: (Condition.snowy_rainy, "overcast, some sleet"),
    11: (Condition.snowy, "overcast, some snow showers"),
    12: (Condition.lightning, "sunny intervals, chance of thunderstorms"),
    13: (Condition.lightning_rainy, "sunny intervals, possible thunderstorms"),
    14: (Condition.rainy, "very cloudy, light rain"),
    15: (Condition.snowy_rainy, "very cloudy, light sleet"),
    16: (Condition.snowy, "very cloudy, light snow showers"),
    17: (Condition.rainy, "very cloudy, intermittent rain"),
    18: (Condition.snowy_rainy, "very cloudy, intermittent sleet"),
    19: (Condition.snowy, "very cloudy, intermittent snow"),
    20: (Condition.pouring, "very overcast with rain"),
    21: (Condition.snowy_rainy, "very overcast with frequent sleet"),
    22: (Condition.snowy, "very overcast with heavy snow"),
    23: (Condition.lightning_rainy, "very overcast, slight chance of storms"),
    24: (Condition.lightning_rainy, "very overcast with storms"),
    25: (Condition.lightning_rainy, "very cloudy, very stormy"),
    26: (Condition.sunny, "high clouds"),
    27: (Condition.fog, "stratus"),
    28: (Condition.fog, "fog"),
    29: (Condition.rainy, "sunny intervals, scattered showers"),
    30: (Condition.snowy, "sunny intervals, scattered snow showers"),
    31: (Condition.snowy_rainy, "sunny intervals, scattered sleet"),
    32: (Condition.lightning_rainy, "sunny intervals, some showers"),
    33: (Condition.rainy, "short sunny intervals, frequent rain"),
    34: (Condition.snowy, "short sunny intervals, frequent snowfalls"),
    35: (Condition.cloudy, "overcast and dry"),
    36: (Condition.lightning, "partly sunny, slightly stormy"),
    37: (Condition.snowy, "partly sunny, stormy snow showers"),
    38: (Condition.lightning_rainy, "overcast, thundery showers"),
    39: (Condition.snowy_rainy, "overcast, thundery snow showers"),
    40: (Condition.lightning, "very cloudly, slightly stormy"),
    41: (Condition.lightning, "overcast, slightly stormy"),
    42: (Condition.snowy, "very cloudly, thundery snow showers"),
    101: (Condition.clear_night, "clear"),
    102: (Condition.partly_cloudy, "slightly overcast"),
    103: (Condition.partly_cloudy, "heavy cloud formations"),
    104: (Condition.partly_cloudy, "overcast"),
    105: (Condition.cloudy, "very cloudy"),
    106: (Condition.rainy, "overcast, scattered showers"),
    107: (Condition.snowy_rainy, "overcast, scattered rain and snow showers"),
    108: (Condition.snowy, "overcast, snow showers"),
    109: (Condition.rainy, "overcast, some showers"),
    110: (Condition.snowy_rainy, "overcast, some rain and snow showers"),
    111: (Condition.snowy, "overcast, some snow showers"),
    112: (Condition.lightning, "slightly stormy"),
    113: (Condition.lightning_rainy, "storms"),
    114: (Condition.rainy, "very cloudy, light rain"),
    115: (Condition.snowy_rainy, "very cloudy, light rain and snow showers"),
    116: (Condition.snowy, "very cloudy, light snowfall"),
    117: (Condition.rainy, "very cloudy, intermittent rain"),
    118: (Condition.snowy_rainy, "very cloudy, intermittant mixed rain and snowfall"),
    119: (Condition.snowy, "very cloudy, intermittent snowfall"),
    120: (Condition.pouring, "very cloudy, constant rain"),
    121: (Condition.snowy_rainy, "very cloudy, frequent rain and snowfall"),
    122: (Condition.snowy, "very cloudy, heavy snowfall"),
    123: (Condition.lightning_rainy, "very cloudy, slightly stormy"),
    124: (Condition.lightning_rainy, "very cloudy, stormy"),
    125: (Condition.lightning_rainy, "very cloudy, storms"),
    126: (Condition.cloudy, "high cloud"),
    127: (Condition.fog, "stratus"),
    128: (Condition.fog, "fog"),
    129: (Condition.rainy, "slightly overcast, scattered showers"),
    130: (Condition.snowy, "slightly overcast, scattered snowfall"),
    131: (Condition.snowy_rainy, "slightly overcast, rain and snow showers"),
    132: (Condition.lightning_rainy, "slightly overcast, some showers"),
    133: (Condition.rainy, "overcast, frequent snow showers"),
    134: (Condition.snowy, "overcast, frequent snow showers"),
    135: (Condition.cloudy, "overcast and dry"),
    136: (Condition.lightning, "slightly overcast, slightly stormy"),
    137: (Condition.snowy, "slightly overcast, stormy snow showers"),
    138: (Condition.lightning_rainy, "overcast, thundery showers"),
    139: (Condition.snowy_rainy, "overcast, thundery snow showers"),
    140: (Condition.lightning, "very cloudly, slightly stormy"),
    141: (Condition.lightning, "overcast, slightly stormy"),
    142: (Condition.snowy, "very cloudly, thundery snow showers"),
}

SENSOR_TYPE_NAME = "name"
SENSOR_TYPE_UNIT = "unit"
SENSOR_TYPE_ICON = "icon"
SENSOR_TYPE_CLASS = "device_class"
SENSOR_DATA_ID = "msDataId"

SENSOR_TYPES = {
    "temperature": {
        SENSOR_TYPE_NAME: "Temperature",
        SENSOR_TYPE_UNIT: UnitOfTemperature.CELSIUS,
        SENSOR_TYPE_ICON: "mdi:thermometer",
        SENSOR_TYPE_CLASS: SensorDeviceClass.TEMPERATURE,
        SENSOR_DATA_ID: "tre200s0",
    },
    "10minrain": {
        SENSOR_TYPE_NAME: "Precipitation",
        SENSOR_TYPE_UNIT: UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        SENSOR_TYPE_ICON: "mdi:water",
        SENSOR_TYPE_CLASS: SensorDeviceClass.PRECIPITATION,
        SENSOR_DATA_ID: "rre150z0",
    },
    "10minsun": {
        SENSOR_TYPE_NAME: "Sunshine Duration",
        SENSOR_TYPE_UNIT: UnitOfTime.MINUTES,
        SENSOR_TYPE_ICON: "mdi:weather-sunny",
        SENSOR_TYPE_CLASS: SensorDeviceClass.DURATION,
        SENSOR_DATA_ID: "sre000z0",
    },
    "sun_radiant": {
        SENSOR_TYPE_NAME: "Solar Irradiation",
        SENSOR_TYPE_UNIT: UnitOfIrradiance.WATTS_PER_SQUARE_METER,
        SENSOR_TYPE_ICON: "mdi:weather-sunny",
        SENSOR_TYPE_CLASS: SensorDeviceClass.IRRADIANCE,
        SENSOR_DATA_ID: "gre000z0",
    },
    "humidity": {
        SENSOR_TYPE_NAME: "Humidity",
        SENSOR_TYPE_UNIT: PERCENTAGE,
        SENSOR_TYPE_ICON: "mdi:water-percent",
        SENSOR_TYPE_CLASS: SensorDeviceClass.HUMIDITY,
        SENSOR_DATA_ID: "ure200s0",
    },
    "dew_point": {
        SENSOR_TYPE_NAME: "Dew Point",
        SENSOR_TYPE_UNIT: UnitOfTemperature.CELSIUS,
        SENSOR_TYPE_ICON: "mdi:weather-fog",
        SENSOR_TYPE_CLASS: SensorDeviceClass.TEMPERATURE,
        SENSOR_DATA_ID: "tde200s0",
    },
    "wind_direction": {
        SENSOR_TYPE_NAME: "Wind Direction",
        SENSOR_TYPE_UNIT: DEGREE,
        SENSOR_TYPE_ICON: "mdi:compass-rose",
        SENSOR_TYPE_CLASS: None, # Es gibt keine Wind-Direction-Klasse in HA
        SENSOR_DATA_ID: "dkl010z0",
    },
    "wind_speed": {
        SENSOR_TYPE_NAME: "Wind Speed",
        SENSOR_TYPE_UNIT: UnitOfSpeed.KILOMETERS_PER_HOUR,
        SENSOR_TYPE_ICON: "mdi:weather-windy",
        SENSOR_TYPE_CLASS: SensorDeviceClass.WIND_SPEED,
        SENSOR_DATA_ID: "fu3010z0",
    },
    "wind_speed_max": {
        SENSOR_TYPE_NAME: "Wind Gust",
        SENSOR_TYPE_UNIT: UnitOfSpeed.KILOMETERS_PER_HOUR,
        SENSOR_TYPE_ICON: "mdi:weather-windy",
        SENSOR_TYPE_CLASS: SensorDeviceClass.WIND_SPEED,
        SENSOR_DATA_ID: "fu3010z1",
    },
    "pressure": {
        SENSOR_TYPE_NAME: "Pressure (QFE)",
        SENSOR_TYPE_UNIT: UnitOfPressure.HPA,
        SENSOR_TYPE_ICON: "mdi:gauge",
        SENSOR_TYPE_CLASS: SensorDeviceClass.PRESSURE,
        SENSOR_DATA_ID: "prestas0",
    },
    "pressure_qff": {
        SENSOR_TYPE_NAME: "Pressure (QFF)",
        SENSOR_TYPE_UNIT: UnitOfPressure.HPA,
        SENSOR_TYPE_ICON: "mdi:gauge",
        SENSOR_TYPE_CLASS: SensorDeviceClass.PRESSURE,
        SENSOR_DATA_ID: "pp0qffs0",
    },
    "pressure_qnh": {
        SENSOR_TYPE_NAME: "Pressure (QNH)",
        SENSOR_TYPE_UNIT: UnitOfPressure.HPA,
        SENSOR_TYPE_ICON: "mdi:gauge",
        SENSOR_TYPE_CLASS: SensorDeviceClass.PRESSURE,
        SENSOR_DATA_ID: "pp0qnhs0",
    },
}
