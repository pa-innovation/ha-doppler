"""Constants for Sandman Doppler Clocks."""
# Base component constants
NAME = "Sandman Doppler"
DOMAIN = "sandman_doppler"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "0.0.1"
ISSUE_URL = "https://github.com/pa-innovation/ha-doppler/issues"

# Platforms
PLATFORMS = ["light", "number", "select", "switch"]

# Data keys
ATTR_DAY_BUTTON_COLOR = "day_button_color"
ATTR_NIGHT_BUTTON_COLOR = "night_button_color"
ATTR_DAY_DISPLAY_COLOR = "day_display_color"
ATTR_NIGHT_DISPLAY_COLOR = "night_display_color"
ATTR_DAY_DISPLAY_BRIGHTNESS = "day_display_brightness"
ATTR_NIGHT_DISPLAY_BRIGHTNESS = "night_display_brightness"
ATTR_DAY_BUTTON_BRIGHTNESS = "day_button_brightness"
ATTR_NIGHT_BUTTON_BRIGHTNESS = "night_button_brightness"
ATTR_AUTO_BRIGHTNESS_ENABLED = "auto_brightness_enabled"
ATTR_VOLUME_LEVEL = "volume_level"
ATTR_ALARMS = "alarms"
ATTR_ALARM_SOUNDS = "alarm_sounds"
ATTR_TIME_MODE = "time_mode"
ATTR_DOTW_STATUS = "dotw_status"
ATTR_WEATHER = "weather"
ATTR_WIFI = "wifi"
ATTR_COLON_BLINK = "colon_blink"
ATTR_USE_COLON = "use_colon"
ATTR_USE_LEADING_ZERO = "use_leading_zero"
ATTR_DISPLAY_SECONDS = "display_seconds"
ATTR_ALEXA_USE_ASCENDING_ALARMS = "alexa_ascending_alarms"
ATTR_ALEXA_TAPTALK_TONE = "alexa_taptalk_tone"
ATTR_ALEXA_WAKEWORD_TONE = "alexa_wakeword_tone"
ATTR_SOUND_PRESET = "sound_preset"
ATTR_SOUND_PRESET_MODE = "sound_preset_mode"

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
