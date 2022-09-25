"""Constants for Sandman Doppler Clocks."""
from homeassistant.const import Platform

# Base component constants
NAME = "Sandman Doppler"
DOMAIN = "sandman_doppler"

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

ATTR_DSN = "dsn"
ATTR_BUTTON = "button"
CONF_SUBTYPE = "subtype"
