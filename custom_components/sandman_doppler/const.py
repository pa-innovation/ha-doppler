"""Constants for Sandman Doppler Clocks."""

# Base component constants
NAME = "Sandman Doppler"
DOMAIN = "sandman_doppler"

ATTR_DSN = "dsn"
ATTR_BUTTON = "button"
CONF_SUBTYPE = "subtype"

ATTR_DOPPLER_NAME = "doppler_name"

EVENT_BUTTON_PRESSED = f"{DOMAIN}_button_pressed"

SERVICE_SET_WEATHER_LOCATION = "set_weather_location"
SERVICE_ADD_ALARM = "add_alarm"
SERVICE_UPDATE_ALARM = "update_alarm"
SERVICE_DELETE_ALARM = "delete_alarm"
SERVICE_UPDATE_ALARM = "update_alarm"
SERVICE_SET_MAIN_DISPLAY_TEXT = "set_main_display_text"
SERVICE_SET_MINI_DISPLAY_NUMBER = "set_mini_display_number"
SERVICE_SET_RAINBOW_MODE = "set_rainbow_mode"
SERVICE_ACTIVATE_LIGHT_BAR_BLINK = "activate_light_bar_blink"
SERVICE_ACTIVATE_LIGHT_BAR_COMET = "activate_light_bar_comet"
SERVICE_ACTIVATE_LIGHT_BAR_PULSE = "activate_light_bar_pulse"
SERVICE_ACTIVATE_LIGHT_BAR_SET = "activate_light_bar_set"
SERVICE_ACTIVATE_LIGHT_BAR_SET_EACH = "activate_light_bar_set_each"
SERVICE_ACTIVATE_LIGHT_BAR_SWEEP = "activate_light_bar_sweep"
