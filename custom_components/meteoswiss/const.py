"""Constants for MeteoSwiss."""

from __future__ import annotations

from enum import StrEnum

from homeassistant.const import (
    CONF_NAME,
    DEGREE,
    PERCENTAGE,
    UnitOfIrradiance,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
)

DOMAIN = "meteoswiss"
CONF_NAME = CONF_NAME
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

STATION_URL = "https://rudd-o.com/meteostations"


class Condition(StrEnum):
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


# Mapping for conditions vs icon ID of meteoswiss
# ID < 100 for day icons
# ID > 100 for night icons
# MeteoSwiss has more lvl for cloudy an rainy than home assistant
# https://www.meteoswiss.admin.ch/dam/jcr:bfcea855-ab6b-4602-9d8b-0464afa30e66/2022-02-14-Wetter-Icons-inkl-beschreibung-v1-an-website.xlsx
# Dump from the spreadsheet linked above on August 23 2024.
# Massaged to convert to Python enum.
CODE_TO_CONDITION_MAP = {
    1: (Condition.sunny, "sunny"),
    2: (Condition.partly_cloudy, "mostly sunny, some clouds"),
    3: (Condition.partly_cloudy, "partly sunny, thick passing clouds"),
    4: (Condition.partly_cloudy, "overcast"),
    5: (Condition.cloudy, "very cloudy"),
    6: (Condition.rainy, "sunny intervals,  isolated showers"),
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
    115: (Condition.snowy_rainy, "very cloudy, light rain and snow  showers"),
    116: (Condition.snowy, "very cloudy, light snowfall"),
    117: (Condition.rainy, "very cloudy, intermittent rain"),
    118: (Condition.snowy_rainy, "very cloudy, intermittant mixed rain and snowfall"),
    119: (Condition.snowy, "very cloudy, intermittent snowfall"),
    120: (Condition.pouring, "very cloudy,  constant rain"),
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

"""
From https://data.geo.admin.ch/ch.meteoschweiz.messwerte-aktuell/info/VQHA80_de.txt :

Legende für VQHA80
Station/Location;yyyyMMddHHmm;tre200s0;rre150z0;sre000z0;gre000z0;ure200s0;tde200s0;dkl010z0;fu3010z0;fu3010z1;prestas0;pp0qffs0;pp0qnhs0;ppz850s0;ppz700s0;dv1towz0;fu3towz0;fu3towz1;ta1tows0;uretows0;tdetows0     

Station/Location https://data.geo.admin.ch/ch.meteoschweiz.messnetz-automatisch/ch.meteoschweiz.messnetz-automatisch_de.csv

Zeitangaben in UTC: 00:40 UTC = 02:40 Sommerzeit
                              = 01:40 Winterzeit

Fehlende Messwerte            -

Parameter    Einheit        Beschreibung
tre200s0     °C             Lufttemperatur 2 m über Boden; Momentanwert
rre150z0     mm             Niederschlag; Zehnminutensumme
sre000z0     min            Sonnenscheindauer; Zehnminutensumme
gre000z0     W/m²           Globalstrahlung; Zehnminutenmittel
ure200s0     %              Relative Luftfeuchtigkeit 2 m über Boden; Momentanwert
tde200s0     °C             Taupunkt 2 m über Boden; Momentanwert
dkl010z0     °              Windrichtung; Zehnminutenmittel
fu3010z0     km/h           Windgeschwindigkeit; Zehnminutenmittel
fu3010z1     km/h           Böenspitze (Sekundenböe); Maximum
prestas0     hPa            Luftdruck auf Stationshöhe (QFE); Momentanwert
pp0qffs0     hPa            Luftdruck reduziert auf Meeresniveau (QFF); Momentanwert
pp0qnhs0     hPa            Luftdruck reduziert auf Meeresniveau mit Standardatmosphäre (QNH); Momentanwert
ppz850s0     gpm            Geopotentielle Höhe der 850 hPa-Fläche; Momentanwert
ppz700s0     gpm            Geopotentielle Höhe der 700 hPa-Fläche; Momentanwert
dv1towz0     °              Windrichtung vektoriell; Zehnminutenmittel; Instrument 1
fu3towz0     km/h           Windgeschwindigkeit Turm; Zehnminutenmittel
fu3towz1     km/h           Böenspitze (Sekundenböe) Turm; Maximum
ta1tows0     °C             Lufttemperatur Instrument 1
uretows0     %              Relative Luftfeuchtigkeit Turm; Momentanwert
tdetows0     °C             Taupunkt Turm
"""
SENSOR_TYPES = {
    "temperature": {
        SENSOR_TYPE_NAME: "temperature",
        SENSOR_TYPE_UNIT: UnitOfTemperature.CELSIUS,
        SENSOR_TYPE_ICON: "mdi:thermometer",
        SENSOR_TYPE_CLASS: "temperature",
        SENSOR_DATA_ID: "tre200s0",
    },
    "10minrain": {
        SENSOR_TYPE_NAME: "10 minute rain",
        SENSOR_TYPE_UNIT: "mm",
        SENSOR_TYPE_ICON: "mdi:water",
        SENSOR_TYPE_CLASS: None,
        SENSOR_DATA_ID: "rre150z0",
    },
    "10minsun": {
        SENSOR_TYPE_NAME: "10 minute sun",
        SENSOR_TYPE_UNIT: UnitOfTime.MINUTES,
        SENSOR_TYPE_ICON: "mdi:weather-sunny",
        SENSOR_TYPE_CLASS: None,
        SENSOR_DATA_ID: "sre000z0",
    },
    "sun_radiant": {
        SENSOR_TYPE_NAME: "sun irradiation",
        SENSOR_TYPE_UNIT: UnitOfIrradiance.WATTS_PER_SQUARE_METER,
        SENSOR_TYPE_ICON: "mdi:weather-sunny",
        SENSOR_TYPE_CLASS: None,
        SENSOR_DATA_ID: "gre000z0",
    },
    "humidity": {
        SENSOR_TYPE_NAME: "humidity",
        SENSOR_TYPE_UNIT: PERCENTAGE,
        SENSOR_TYPE_ICON: "mdi:water-percent",
        SENSOR_TYPE_CLASS: None,
        SENSOR_DATA_ID: "ure200s0",
    },
    "dew_point": {
        SENSOR_TYPE_NAME: "dew point",
        SENSOR_TYPE_UNIT: UnitOfTemperature.CELSIUS,
        SENSOR_TYPE_ICON: "mdi:weather-fog",
        SENSOR_TYPE_CLASS: None,
        SENSOR_DATA_ID: "tde200s0",
    },
    "wind_direction": {
        SENSOR_TYPE_NAME: "wind direction",
        SENSOR_TYPE_UNIT: DEGREE,
        SENSOR_TYPE_ICON: "mdi:compass-rose",
        SENSOR_TYPE_CLASS: None,
        SENSOR_DATA_ID: "dkl010z0",
    },
    "wind_speed": {
        SENSOR_TYPE_NAME: "wind speed",
        SENSOR_TYPE_UNIT: UnitOfSpeed.KILOMETERS_PER_HOUR,
        SENSOR_TYPE_ICON: "mdi:weather-windy",
        SENSOR_TYPE_CLASS: None,
        SENSOR_DATA_ID: "fu3010z0",
    },
    "wind_speed_max": {
        SENSOR_TYPE_NAME: "wind speed max",
        SENSOR_TYPE_UNIT: UnitOfSpeed.KILOMETERS_PER_HOUR,
        SENSOR_TYPE_ICON: "mdi:weather-windy",
        SENSOR_TYPE_CLASS: None,
        SENSOR_DATA_ID: "fu3010z1",
    },
    "pressure": {
        SENSOR_TYPE_NAME: "pressure",
        SENSOR_TYPE_UNIT: UnitOfPressure.HPA,
        SENSOR_TYPE_ICON: "mdi:gauge",
        SENSOR_TYPE_CLASS: None,
        SENSOR_DATA_ID: "prestas0",
    },
    "pressure_qff": {
        SENSOR_TYPE_NAME: "pressure QFF",
        SENSOR_TYPE_UNIT: UnitOfPressure.HPA,
        SENSOR_TYPE_ICON: "mdi:gauge",
        SENSOR_TYPE_CLASS: None,
        SENSOR_DATA_ID: "pp0qffs0",
    },
    "pressure_qnh": {
        SENSOR_TYPE_NAME: "pressure QNH",
        SENSOR_TYPE_UNIT: UnitOfPressure.HPA,
        SENSOR_TYPE_ICON: "mdi:gauge",
        SENSOR_TYPE_CLASS: None,
        SENSOR_DATA_ID: "pp0qnhs0",
    },
}
