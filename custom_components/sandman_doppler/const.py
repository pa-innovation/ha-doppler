"""Constants for Sandman Doppler Clocks."""
from homeassistant.const import Platform

# Base component constants
NAME = "Sandman Doppler"
DOMAIN = "sandman_doppler"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "0.0.1"
ISSUE_URL = "https://github.com/pa-innovation/ha-doppler/issues"

# Platforms
PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

# Configuration and options
CONF_ENABLED = "enabled"

# Defaults
DEFAULT_NAME = DOMAIN


STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""


# Weather modes
WEATHER_OPTIONS = [
    "Off",  # 0
    "Daily Max F",  # 1
    "Daily Max C",  # 2
    "Daily Avg Humidity",  # 3
    "Daily AQI",  # 4
    "Daily Min F",  # 5
    "Daily Min C",  # 6
    "Daily Humidity Min",  # 7
    "Daily Humididy Max",  # 8
    "Hourly F",  # 9
    "Hourly C",  # 10
    "Hourly Humidity",  # 11
    "Hourly AQI",  # 12
    "NWS Daily Forecast F",  # 13
    "NWS Daily Forecast C",  # 14
    "NWS Hourly Observation F",  # 15
    "NWS Hourly Observation C",  # 16
    "NWS Hourly Humidity",  # 17
]

SANDMAN_DOPPLER_BUTTON = "sandman_doppler_button"
ATTR_DSN = "dsn"
ATTR_BUTTON = "button"
CONF_SUBTYPE = "subtype"
