"""Constants for Sandman Doppler Clocks."""
# Base component constants
NAME = "Sandman Doppler"
DOMAIN = "sandman_doppler"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "0.0.1"
ISSUE_URL = "https://github.com/pa-innovation/ha-doppler/issues"

# Platforms
PLATFORMS = ["light", "number", "select"]

# Data keys
ATTR_BUTTON_COLOR = "button_color"
ATTR_DISPLAY_COLOR = "display_color"
ATTR_DISPLAY_BRIGHTNESS = "display_brightness"
ATTR_AUTO_BRIGHTNESS_ENABLED = "auto_brightness_enabled"
ATTR_VOLUME_LEVEL = "volume_level"
ATTR_ALARMS = "alarms"
ATTR_ALARM_SOUNDS = "alarm_sounds"
ATTR_TIME_MODE = "time_mode"
ATTR_DOTW_STATUS = "dotw_status"
ATTR_WEATHER = "weather"
ATTR_WIFI = "wifi"


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
