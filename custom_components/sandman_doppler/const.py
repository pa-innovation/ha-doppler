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
    Platform.SIREN,
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

SANDMAN_DOPPLER_BUTTON = "sandman_doppler_button"
ATTR_DSN = "dsn"
ATTR_BUTTON = "button"
CONF_SUBTYPE = "subtype"
