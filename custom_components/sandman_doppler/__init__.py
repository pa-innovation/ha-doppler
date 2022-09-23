"""The Sandman Doppler integration."""
from __future__ import annotations

from typing import Any
import asyncio
from datetime import timedelta
import logging
from aiohttp.client import ClientTimeout, DEFAULT_TIMEOUT

from doppyler.client import DopplerClient
from doppyler.model.doppler import Doppler
from doppyler.model.alarm import Alarm, AlarmStatus, AlarmSource, AlarmDict
from doppyler.model.color import Color, ColorDict
from doppyler.model.main_display_text import MainDisplayText, MainDisplayTextDict
from doppyler.model.mini_display_number import MiniDisplayNumber, MiniDisplayNumberDict
from doppyler.model.light_bar import LightbarDisplayDict, LightbarDisplayEffect

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.service import ServiceCall
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed


from .const import (
    ATTR_ALARM_SOUNDS,
    ATTR_ALARMS,
    ATTR_AUTO_BRIGHTNESS_ENABLED,
    ATTR_DAY_BUTTON_COLOR,
    ATTR_NIGHT_BUTTON_COLOR,
    ATTR_DAY_DISPLAY_BRIGHTNESS,
    ATTR_NIGHT_DISPLAY_BRIGHTNESS,
    ATTR_DAY_BUTTON_BRIGHTNESS,
    ATTR_NIGHT_BUTTON_BRIGHTNESS,
    ATTR_DAY_DISPLAY_COLOR,
    ATTR_NIGHT_DISPLAY_COLOR,
    ATTR_DOTW_STATUS,
    ATTR_TIME_MODE,
    ATTR_VOLUME_LEVEL,
    ATTR_WEATHER,
    ATTR_WIFI,
    ATTR_COLON_BLINK,
    ATTR_USE_COLON,
    ATTR_USE_LEADING_ZERO,
    ATTR_DISPLAY_SECONDS,
    ATTR_ALEXA_USE_ASCENDING_ALARMS,
    ATTR_ALEXA_TAPTALK_TONE,
    ATTR_ALEXA_WAKEWORD_TONE,
    ATTR_SOUND_PRESET,
    ATTR_SOUND_PRESET_MODE,
    ATTR_WEATHER_ON,
    ATTR_WEATHER_MODE,
    ATTR_LIGHTSENSOR_VALUE,
    ATTR_DAYNIGHTMODE_VALUE,
    ATTR_TIMEOFFSET,
    ATTR_TIMEZONE,
    WEATHER_OPTIONS,
    DOMAIN,
    PLATFORMS,
    STARTUP_MESSAGE,
)

SCAN_INTERVAL = timedelta(seconds=900)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Setup integration."""
    _LOGGER.info(STARTUP_MESSAGE)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up config entry."""
    hass.data.setdefault(DOMAIN, {})

    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]

    session = async_create_clientsession(hass, timeout=ClientTimeout(DEFAULT_TIMEOUT))
    client = DopplerClient(email, password, client_session=session, local_control=False)

    coordinator = DopplerDataUpdateCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    mydevices = await client.get_devices()
    for device in mydevices.values():
        await device.set_sync_button_display_color(False)
        await device.set_sync_day_night_color(False)
        await device.set_sync_button_display_brightness(False)

    # async def handle_set_alarm_service(call: ServiceCall) -> None:
    #     deviceregistry = dr.async_get(hass)
    #     deviceentry = deviceregistry.async_get(call.data["doppler_device_id"])
    #     _LOGGER.warning(
    #         f"Calling setalarm {call.data['alarm_time']} {deviceentry.identifiers}"
    #     )
    #     _LOGGER.warning(f"printing config entries{deviceentry.config_entries}")
    #     mydevice = ""
    #     for device in mydevices.values():
    #         if ("sandman_doppler", device.id) in deviceentry.identifiers:
    #             _LOGGER.warning(f"managed to locate the device id")
    #             mydevice = device
    #             break
    #     if mydevice != "":
    #         if "repeat" in call.data:
    #             r = call.data["repeat"]
    #         else:
    #             r = ""
    #         alarmdict = AlarmDict(
    #             id=int(call.data["alarm_id"]),
    #             name=call.data["alarm_name"],
    #             time_hr=int(call.data["alarm_time"].split(":")[0]),
    #             time_min=int(call.data["alarm_time"].split(":")[1]),
    #             repeat=r,
    #             color=ColorDict(
    #                 red=int(call.data["color"][0]),
    #                 green=int(call.data["color"][1]),
    #                 blue=int(call.data["color"][2]),
    #             ),
    #             volume=int(call.data["volume"]),
    #             status=AlarmStatus.SET,
    #             src=AlarmSource.APP,
    #             sound=call.data["sound"],
    #         )

    #         alarm = Alarm(mydevice, alarmdict)
    #         result = await client.append_new_alarm(mydevice, alarm)
    #         _LOGGER.warning(f"alarm result was {result}")

    # async def handle_delete_alarm_service(call: ServiceCall) -> None:
    #     deviceregistry = dr.async_get(hass)
    #     deviceentry = deviceregistry.async_get(call.data["doppler_device_id"])
    #     mydevice = ""
    #     for device in mydevices.values():
    #         if ("sandman_doppler", device.id) in deviceentry.identifiers:
    #             _LOGGER.warning(f"managed to locate the device id")
    #             mydevice = device
    #             break
    #     if mydevice != "":
    #         await client.delete_alarm(mydevice, int(call.data["alarm_id"]))

    # async def handle_set_main_display_service(call: ServiceCall) -> None:
    #     deviceregistry = dr.async_get(hass)
    #     deviceentry = deviceregistry.async_get(call.data["doppler_device_id"])
    #     mydevice = ""
    #     for device in mydevices.values():
    #         if ("sandman_doppler", device.id) in deviceentry.identifiers:
    #             _LOGGER.warning(f"got device id in handle_set_main_display")
    #             mydevice = device
    #             break
    #     if mydevice != "":
    #         _LOGGER.warning(f"Called handle_set_main_display_service")
    #         mdt_dict = MainDisplayTextDict(
    #             {
    #                 "text": str(call.data["display_text"]),
    #                 "duration": int(call.data["display_duration"]),
    #                 "speed": int(call.data["display_speed"]),
    #                 "color": [
    #                     int(call.data["display_color"][0]),
    #                     int(call.data["display_color"][1]),
    #                     int(call.data["display_color"][2]),
    #                 ],
    #             }
    #         )

    #         m = MainDisplayText(mydevice, mdt_dict)
    #         _LOGGER.warning(f"m={m.to_dict()}")
    #         await client.set_main_display_text(
    #             mydevice, MainDisplayText(mydevice, mdt_dict)
    #         )

    # async def handle_set_mini_display_service(call: ServiceCall) -> None:
    #     deviceregistry = dr.async_get(hass)
    #     deviceentry = deviceregistry.async_get(call.data["doppler_device_id"])
    #     mydevice = ""
    #     for device in mydevices.values():
    #         if ("sandman_doppler", device.id) in deviceentry.identifiers:
    #             _LOGGER.warning(f"got device id in handle_set_mini_display_service")
    #             mydevice = device
    #             break
    #     if mydevice != "":
    #         _LOGGER.warning(f"Called handle_display_num_mini_service")
    #         mdn_dict = MiniDisplayNumberDict(
    #             {
    #                 "num": int(call.data["display_number"]),
    #                 "duration": int(call.data["display_duration"]),
    #                 "color": [
    #                     int(call.data["display_color"][0]),
    #                     int(call.data["display_color"][1]),
    #                     int(call.data["display_color"][2]),
    #                 ],
    #             }
    #         )

    #         await client.set_mini_display_number(
    #             mydevice, MiniDisplayNumber(mydevice, mdn_dict)
    #         )

    # async def handle_set_lightbar_color_service(call: ServiceCall) -> None:
    #     deviceregistry = dr.async_get(hass)
    #     deviceentry = deviceregistry.async_get(call.data["doppler_device_id"])
    #     mydevice = ""
    #     for device in mydevices.values():
    #         if ("sandman_doppler", device.id) in deviceentry.identifiers:
    #             _LOGGER.warning(f"got device id in handle_set_lightbar")
    #             mydevice = device
    #             break
    #     if mydevice != "":
    #         _LOGGER.warning(f"data was {call.data}")
    #         _LOGGER.warning(f"Called handle_set_lightbar_color_service")
    #         color_list = []
    #         for c in [
    #             call.data.get("lightbar_color1"),
    #             call.data.get("lightbar_color2"),
    #             call.data.get("lightbar_color3"),
    #             call.data.get("lightbar_color4"),
    #             call.data.get("lightbar_color5"),
    #             call.data.get("lightbar_color6"),
    #             call.data.get("lightbar_color7"),
    #             call.data.get("lightbar_color8"),
    #             call.data.get("lightbar_color9"),
    #             call.data.get("lightbar_color10"),
    #             call.data.get("lightbar_color11"),
    #             call.data.get("lightbar_color12"),
    #         ]:
    #             if c is not None:
    #                 color_list.append([c[0], c[1], c[2]])
    #         s = call.data.get("lightbar_sparkle")
    #         r = call.data.get("lightbar_rainbow")

    #         attributes_dict = {}
    #         attributes_dict["display"] = "set"
    #         if s is not None:
    #             attributes_dict["sparkle"] = f"{s}"
    #         if r is not None:
    #             if r is True:
    #                 attributes_dict["rainbow"] = str("true")
    #             else:
    #                 attributes_dict["rainbow"] = str("false")

    #         lbde_dict = LightbarDisplayDict(
    #             {
    #                 "colors": color_list,
    #                 "duration": int(call.data["lightbar_duration"]),
    #                 "speed": int(call.data["lightbar_speed"]),
    #                 "attributes": attributes_dict,
    #             }
    #         )
    #         _LOGGER.warning(f"lbde_dict={lbde_dict}")
    #         retval = await client.set_lightbar_effect(
    #             mydevice, LightbarDisplayEffect(mydevice, lbde_dict)
    #         )
    #         _LOGGER.warning(f"retval={retval.to_dict()}")

    # async def handle_set_each_lightbar_color_service(call: ServiceCall) -> None:
    #     deviceregistry = dr.async_get(hass)
    #     deviceentry = deviceregistry.async_get(call.data["doppler_device_id"])
    #     mydevice = ""
    #     for device in mydevices.values():
    #         if ("sandman_doppler", device.id) in deviceentry.identifiers:
    #             _LOGGER.warning(f"got device id in handle_set_lightbar")
    #             mydevice = device
    #             break
    #     if mydevice != "":
    #         _LOGGER.warning(f"data was {call.data}")
    #         _LOGGER.warning(f"Called handle_set_lightbar_color_service")
    #         color_list = []
    #         for c in [
    #             call.data.get("lightbar_color1"),
    #             call.data.get("lightbar_color2"),
    #             call.data.get("lightbar_color3"),
    #             call.data.get("lightbar_color4"),
    #             call.data.get("lightbar_color5"),
    #             call.data.get("lightbar_color6"),
    #             call.data.get("lightbar_color7"),
    #             call.data.get("lightbar_color8"),
    #             call.data.get("lightbar_color9"),
    #             call.data.get("lightbar_color10"),
    #             call.data.get("lightbar_color11"),
    #             call.data.get("lightbar_color12"),
    #             call.data.get("lightbar_color13"),
    #             call.data.get("lightbar_color14"),
    #             call.data.get("lightbar_color15"),
    #             call.data.get("lightbar_color16"),
    #             call.data.get("lightbar_color17"),
    #             call.data.get("lightbar_color18"),
    #             call.data.get("lightbar_color19"),
    #             call.data.get("lightbar_color20"),
    #             call.data.get("lightbar_color21"),
    #             call.data.get("lightbar_color22"),
    #             call.data.get("lightbar_color23"),
    #             call.data.get("lightbar_color24"),
    #             call.data.get("lightbar_color25"),
    #             call.data.get("lightbar_color26"),
    #             call.data.get("lightbar_color27"),
    #             call.data.get("lightbar_color28"),
    #             call.data.get("lightbar_color29"),
    #         ]:
    #             if c is not None:
    #                 color_list.append([c[0], c[1], c[2]])
    #         s = call.data.get("lightbar_sparkle")
    #         r = call.data.get("lightbar_rainbow")

    #         attributes_dict = {}
    #         attributes_dict["display"] = "set-each"
    #         if s is not None:
    #             attributes_dict["sparkle"] = f"{s}"
    #         if r is not None:
    #             if r is True:
    #                 attributes_dict["rainbow"] = str("true")
    #             else:
    #                 attributes_dict["rainbow"] = str("false")

    #         lbde_dict = LightbarDisplayDict(
    #             {
    #                 "colors": color_list,
    #                 "duration": int(call.data["lightbar_duration"]),
    #                 "speed": 0,
    #                 "attributes": attributes_dict,
    #             }
    #         )
    #         _LOGGER.warning(f"lbde_dict={lbde_dict}")
    #         retval = await client.set_lightbar_effect(
    #             mydevice, LightbarDisplayEffect(mydevice, lbde_dict)
    #         )
    #         _LOGGER.warning(f"retval={retval.to_dict()}")

    # async def handle_set_lightbar_blink_service(call: ServiceCall) -> None:
    #     deviceregistry = dr.async_get(hass)
    #     deviceentry = deviceregistry.async_get(call.data["doppler_device_id"])
    #     mydevice = ""
    #     for device in mydevices.values():
    #         if ("sandman_doppler", device.id) in deviceentry.identifiers:
    #             _LOGGER.warning(f"got device id in handle_set_lightbar")
    #             mydevice = device
    #             break
    #     if mydevice != "":
    #         _LOGGER.warning(f"data was {call.data}")
    #         _LOGGER.warning(f"Called handle_set_lightbar_color_service")
    #         color_list = []
    #         for c in [
    #             call.data.get("lightbar_color1"),
    #             call.data.get("lightbar_color2"),
    #             call.data.get("lightbar_color3"),
    #             call.data.get("lightbar_color4"),
    #             call.data.get("lightbar_color5"),
    #             call.data.get("lightbar_color6"),
    #             call.data.get("lightbar_color7"),
    #             call.data.get("lightbar_color8"),
    #             call.data.get("lightbar_color9"),
    #             call.data.get("lightbar_color10"),
    #             call.data.get("lightbar_color11"),
    #             call.data.get("lightbar_color12"),
    #         ]:
    #             if c is not None:
    #                 color_list.append([c[0], c[1], c[2]])
    #         s = call.data.get("lightbar_sparkle")
    #         r = call.data.get("lightbar_rainbow")
    #         sp = call.data.get("lightbar_speed")

    #         attributes_dict = {}
    #         attributes_dict["display"] = "blink"
    #         if s is not None:
    #             attributes_dict["sparkle"] = f"{s}"
    #         if r is not None:
    #             if r == True:
    #                 attributes_dict["rainbow"] = str("true")
    #             else:
    #                 attributes_dict["rainbow"] = str("false")

    #         lbde_dict = LightbarDisplayDict(
    #             {
    #                 "colors": color_list,
    #                 "duration": int(call.data["lightbar_duration"]),
    #                 "speed": int(call.data["lightbar_speed"]),
    #                 "attributes": attributes_dict,
    #             }
    #         )

    #         _LOGGER.warning(f"lbde_dict={lbde_dict}")
    #         retval = await client.set_lightbar_effect(
    #             mydevice, LightbarDisplayEffect(mydevice, lbde_dict)
    #         )
    #         _LOGGER.warning(f"retval={retval.to_dict()}")

    # async def handle_set_lightbar_pulse_service(call: ServiceCall) -> None:
    #     deviceregistry = dr.async_get(hass)
    #     deviceentry = deviceregistry.async_get(call.data["doppler_device_id"])
    #     mydevice = ""
    #     for device in mydevices.values():
    #         if ("sandman_doppler", device.id) in deviceentry.identifiers:
    #             _LOGGER.warning(f"got device id in handle_set_lightbar")
    #             mydevice = device
    #             break
    #     if mydevice != "":
    #         _LOGGER.warning(f"data was {call.data}")
    #         _LOGGER.warning(f"Called handle_set_lightbar_pulse_service")
    #         color_list = []
    #         for c in [
    #             call.data.get("lightbar_color1"),
    #             call.data.get("lightbar_color2"),
    #             call.data.get("lightbar_color3"),
    #             call.data.get("lightbar_color4"),
    #             call.data.get("lightbar_color5"),
    #             call.data.get("lightbar_color6"),
    #             call.data.get("lightbar_color7"),
    #             call.data.get("lightbar_color8"),
    #             call.data.get("lightbar_color9"),
    #             call.data.get("lightbar_color10"),
    #             call.data.get("lightbar_color11"),
    #             call.data.get("lightbar_color12"),
    #         ]:
    #             if c is not None:
    #                 color_list.append([c[0], c[1], c[2]])
    #         s = call.data.get("lightbar_sparkle")
    #         r = call.data.get("lightbar_rainbow")
    #         sp = call.data.get("lightbar_speed")
    #         gp = call.data.get("lightbar_gap")

    #         attributes_dict = {}
    #         attributes_dict["display"] = "pulse"
    #         if gp is not None:
    #             attributes_dict["gap"] = f"{gp}"
    #         if s is not None:
    #             attributes_dict["sparkle"] = f"{s}"
    #         if r is not None:
    #             if r == True:
    #                 attributes_dict["rainbow"] = str("true")
    #             else:
    #                 attributes_dict["rainbow"] = str("false")

    #         lbde_dict = LightbarDisplayDict(
    #             {
    #                 "colors": color_list,
    #                 "duration": int(call.data["lightbar_duration"]),
    #                 "speed": int(call.data["lightbar_speed"]),
    #                 "attributes": attributes_dict,
    #             }
    #         )

    #         _LOGGER.warning(f"lbde_dict={lbde_dict}")
    #         retval = await client.set_lightbar_effect(
    #             mydevice, LightbarDisplayEffect(mydevice, lbde_dict)
    #         )
    #         _LOGGER.warning(f"retval={retval.to_dict()}")

    # async def handle_set_lightbar_comet_service(call: ServiceCall) -> None:
    #     deviceregistry = dr.async_get(hass)
    #     deviceentry = deviceregistry.async_get(call.data["doppler_device_id"])
    #     mydevice = ""
    #     for device in mydevices.values():
    #         if ("sandman_doppler", device.id) in deviceentry.identifiers:
    #             _LOGGER.warning(f"got device id in handle_set_lightbar")
    #             mydevice = device
    #             break
    #     if mydevice != "":
    #         _LOGGER.warning(f"data was {call.data}")
    #         _LOGGER.warning(f"Called handle_set_lightbar_pulse_service")
    #         color_list = []
    #         for c in [
    #             call.data.get("lightbar_color1"),
    #             call.data.get("lightbar_color2"),
    #             call.data.get("lightbar_color3"),
    #             call.data.get("lightbar_color4"),
    #             call.data.get("lightbar_color5"),
    #             call.data.get("lightbar_color6"),
    #             call.data.get("lightbar_color7"),
    #             call.data.get("lightbar_color8"),
    #             call.data.get("lightbar_color9"),
    #             call.data.get("lightbar_color10"),
    #             call.data.get("lightbar_color11"),
    #             call.data.get("lightbar_color12"),
    #         ]:
    #             if c is not None:
    #                 color_list.append([c[0], c[1], c[2]])
    #         s = call.data.get("lightbar_sparkle")
    #         r = call.data.get("lightbar_rainbow")
    #         sz = call.data.get("lightbar_size")
    #         direct = call.data.get("lightbar_direction")

    #         attributes_dict = {}
    #         attributes_dict["display"] = "comet"
    #         if sz is not None:
    #             attributes_dict["size"] = f"{sz}"
    #         else:
    #             attributes_dict["size"] = f"10"
    #         if direct is not None:
    #             attributes_dict["direction"] = f"{direct}"
    #         else:
    #             attributes_dict["direction"] = "right"
    #         if s is not None:
    #             attributes_dict["sparkle"] = f"{s}"
    #         if r is not None:
    #             if r == True:
    #                 attributes_dict["rainbow"] = str("true")
    #             else:
    #                 attributes_dict["rainbow"] = str("false")

    #         lbde_dict = LightbarDisplayDict(
    #             {
    #                 "colors": color_list,
    #                 "duration": int(call.data["lightbar_duration"]),
    #                 "speed": int(call.data["lightbar_speed"]),
    #                 "attributes": attributes_dict,
    #             }
    #         )

    #         _LOGGER.warning(f"lbde_dict={lbde_dict}")
    #         retval = await client.set_lightbar_effect(
    #             mydevice, LightbarDisplayEffect(mydevice, lbde_dict)
    #         )
    #         _LOGGER.warning(f"retval={retval.to_dict()}")

    # async def handle_set_lightbar_sweep_service(call: ServiceCall) -> None:
    #     deviceregistry = dr.async_get(hass)
    #     deviceentry = deviceregistry.async_get(call.data["doppler_device_id"])
    #     mydevice = ""
    #     for device in mydevices.values():
    #         if ("sandman_doppler", device.id) in deviceentry.identifiers:
    #             _LOGGER.warning(f"got device id in handle_set_lightbar")
    #             mydevice = device
    #             break
    #     if mydevice != "":
    #         _LOGGER.warning(f"data was {call.data}")
    #         _LOGGER.warning(f"Called handle_set_lightbar_pulse_service")
    #         color_list = []
    #         for c in [
    #             call.data.get("lightbar_color1"),
    #             call.data.get("lightbar_color2"),
    #             call.data.get("lightbar_color3"),
    #             call.data.get("lightbar_color4"),
    #             call.data.get("lightbar_color5"),
    #             call.data.get("lightbar_color6"),
    #             call.data.get("lightbar_color7"),
    #             call.data.get("lightbar_color8"),
    #             call.data.get("lightbar_color9"),
    #             call.data.get("lightbar_color10"),
    #             call.data.get("lightbar_color11"),
    #             call.data.get("lightbar_color12"),
    #         ]:
    #             if c is not None:
    #                 color_list.append([c[0], c[1], c[2]])
    #         s = call.data.get("lightbar_sparkle")
    #         r = call.data.get("lightbar_rainbow")
    #         sp = call.data.get("lightbar_speed")
    #         gp = call.data.get("lightbar_gap")
    #         sz = call.data.get("lightbar_size")
    #         direct = call.data.get("lightbar_direction")

    #         attributes_dict = {}
    #         attributes_dict["display"] = "sweep"
    #         if gp is not None:
    #             attributes_dict["gap"] = f"{gp}"
    #         if s is not None:
    #             attributes_dict["sparkle"] = f"{s}"
    #         if sz is not None:
    #             attributes_dict["size"] = f"{sz}"
    #         else:
    #             attributes_dict["size"] = "10"
    #         if direct is not None:
    #             attributes_dict["direction"] = f"{direct}"
    #         else:
    #             attributes_dict["direction"] = "right"
    #         if r is not None:
    #             if r is True:
    #                 attributes_dict["rainbow"] = str("true")
    #             else:
    #                 attributes_dict["rainbow"] = str("false")

    #         lbde_dict = LightbarDisplayDict(
    #             {
    #                 "colors": color_list,
    #                 "duration": int(call.data["lightbar_duration"]),
    #                 "speed": int(call.data["lightbar_speed"]),
    #                 "attributes": attributes_dict,
    #             }
    #         )

    #         _LOGGER.warning(f"lbde_dict={lbde_dict}")
    #         retval = await client.set_lightbar_effect(
    #             mydevice, LightbarDisplayEffect(mydevice, lbde_dict)
    #         )
    #         _LOGGER.warning(f"retval={retval.to_dict()}")

    # async def handle_set_display_color_service(call: ServiceCall) -> None:
    #     deviceregistry = dr.async_get(hass)
    #     deviceentry = deviceregistry.async_get(call.data["doppler_device_id"])
    #     mydevice = ""
    #     for device in mydevices.values():
    #         if ("sandman_doppler", device.id) in deviceentry.identifiers:
    #             mydevice = device
    #             break
    #     if mydevice != "":
    #         dayornight = call.data.get("display_day_or_night")
    #         colorval = call.data.get("display_color")

    #         if dayornight == "Day":
    #             retval = await client.set_day_display_color(
    #                 mydevice, Color.from_list(colorval)
    #             )
    #         elif dayornight == "Night":
    #             retval = await client.set_night_display_color(
    #                 mydevice, Color.from_list(colorval)
    #             )
    #         else:
    #             raise Exception("Got None for Dayornight")

    # async def handle_set_button_color_service(call: ServiceCall) -> None:
    #     deviceregistry = dr.async_get(hass)
    #     deviceentry = deviceregistry.async_get(call.data["doppler_device_id"])
    #     mydevice = ""
    #     for device in mydevices.values():
    #         if ("sandman_doppler", device.id) in deviceentry.identifiers:
    #             mydevice = device
    #             break
    #     if mydevice != "":
    #         dayornight = call.data.get("button_day_or_night")
    #         colorval = call.data.get("button_color")

    #         if dayornight == "Day":
    #             retval = await client.set_day_button_color(
    #                 mydevice, Color.from_list(colorval)
    #             )
    #         elif dayornight == "Night":
    #             retval = await client.set_night_button_color(
    #                 mydevice, Color.from_list(colorval)
    #             )
    #         else:
    #             raise Exception("Got None for Dayornight")

    # async def handle_set_display_brightness_service(call: ServiceCall) -> None:
    #     deviceregistry = dr.async_get(hass)
    #     deviceentry = deviceregistry.async_get(call.data["doppler_device_id"])
    #     mydevice = ""
    #     for device in mydevices.values():
    #         if ("sandman_doppler", device.id) in deviceentry.identifiers:
    #             mydevice = device
    #             break
    #     if mydevice != "":
    #         dayornight = call.data.get("display_day_or_night")
    #         brightness = call.data.get("display_brightness")

    #         if dayornight == "Day":
    #             retval = await client.set_day_display_brightness(mydevice, brightness)
    #         elif dayornight == "Night":
    #             retval = await client.set_night_display_brightness(mydevice, brightness)
    #         else:
    #             raise Exception("Got None for Dayornight")

    # async def handle_set_button_brightness_service(call: ServiceCall) -> None:
    #     deviceregistry = dr.async_get(hass)
    #     deviceentry = deviceregistry.async_get(call.data["doppler_device_id"])
    #     mydevice = ""
    #     for device in mydevices.values():
    #         if ("sandman_doppler", device.id) in deviceentry.identifiers:
    #             mydevice = device
    #             break
    #     if mydevice != "":
    #         dayornight = call.data.get("display_day_or_night")
    #         brightness = call.data.get("button_brightness")

    #         if dayornight == "Day":
    #             retval = await client.set_day_button_brightness(mydevice, brightness)
    #         elif dayornight == "Night":
    #             retval = await client.set_night_button_brightness(mydevice, brightness)
    #         else:
    #             raise Exception("Got None for Dayornight")

    # hass.services.async_register(DOMAIN, "setalarmservice", handle_set_alarm_service)
    # hass.services.async_register(
    #     DOMAIN, "deletealarmservice", handle_delete_alarm_service
    # )
    # hass.services.async_register(
    #     DOMAIN, "displaytextmainservice", handle_set_main_display_service
    # )
    # hass.services.async_register(
    #     DOMAIN, "displaynumminiservice", handle_set_mini_display_service
    # )
    # hass.services.async_register(
    #     DOMAIN, "setlightbarcolorservice", handle_set_lightbar_color_service
    # )
    # hass.services.async_register(
    #     DOMAIN, "seteachlightbarcolorservice", handle_set_each_lightbar_color_service
    # )
    # hass.services.async_register(
    #     DOMAIN, "setlightbarblinkservice", handle_set_lightbar_blink_service
    # )
    # hass.services.async_register(
    #     DOMAIN, "setlightbarpulseservice", handle_set_lightbar_pulse_service
    # )
    # hass.services.async_register(
    #     DOMAIN, "setlightbarcometservice", handle_set_lightbar_comet_service
    # )
    # hass.services.async_register(
    #     DOMAIN, "setlightbarsweepservice", handle_set_lightbar_sweep_service
    # )
    # hass.services.async_register(
    #     DOMAIN, "setdisplaycolorservice", handle_set_display_color_service
    # )
    # hass.services.async_register(
    #     DOMAIN, "setbuttoncolorservice", handle_set_button_color_service
    # )
    # hass.services.async_register(
    #     DOMAIN, "setdisplaybrightnessservice", handle_set_display_brightness_service
    # )
    # hass.services.async_register(
    #     DOMAIN, "setbuttonbrightnessservice", handle_set_button_brightness_service
    # )

    return True


class DopplerDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: DopplerClient
    ) -> None:
        """Initialize."""
        self.data: dict[str, dict[str, Any]] = {}
        self.api = client
        self.platforms = []
        self._dev_reg = None
        self._entry = entry

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        _LOGGER.debug("Started _async_update_data")
        if not self._dev_reg:
            self._dev_reg = dr.async_get(self.hass)

        data: dict[str, Any] = {}
        devices: dict[str, Doppler] = {}
        if self.api.devices:
            devices = self.api.devices
        await self.api.get_devices()
        if devices != self.api.devices:
            # TODO: Signal add entities for the new device
            pass

        try:
            for device in self.api.devices.values():
                self._dev_reg.async_get_or_create(
                    config_entry_id=self._entry.entry_id,
                    identifiers={(DOMAIN, device.device_info.dsn)},
                    manufacturer=device.device_info.manufacturer,
                    model=device.device_info.model_number,
                    sw_version=device.device_info.software_version,
                    hw_version=device.device_info.firmware_version,
                    name=device.name,
                )
                device_data = data.setdefault(device.device_info.dsn, {})
                await asyncio.sleep(0.1)
                device_data[ATTR_DAY_BUTTON_COLOR] = await device.get_day_button_color()
                await asyncio.sleep(0.1)
                # _LOGGER.warning("_async_update_data after get_day_button_color")
                # _LOGGER.warning(device_data[ATTR_DAY_BUTTON_COLOR])
                device_data[
                    ATTR_NIGHT_BUTTON_COLOR
                ] = await device.get_night_button_color()
                await asyncio.sleep(0.1)

                device_data[
                    ATTR_DAY_DISPLAY_COLOR
                ] = await device.get_day_display_color()
                await asyncio.sleep(0.1)
                device_data[
                    ATTR_NIGHT_DISPLAY_COLOR
                ] = await device.get_night_display_color()
                await asyncio.sleep(0.1)
                device_data[
                    ATTR_DAY_DISPLAY_BRIGHTNESS
                ] = await device.get_day_display_brightness()
                await asyncio.sleep(0.1)
                device_data[
                    ATTR_NIGHT_DISPLAY_BRIGHTNESS
                ] = await device.get_night_display_brightness()
                await asyncio.sleep(0.1)
                device_data[
                    ATTR_DAY_BUTTON_BRIGHTNESS
                ] = await device.get_day_button_brightness()
                await asyncio.sleep(0.1)

                device_data[
                    ATTR_NIGHT_BUTTON_BRIGHTNESS
                ] = await device.get_night_button_brightness()
                await asyncio.sleep(0.1)
                # device_data[
                #     ATTR_DOTW_STATUS
                # ] = await device.get_day_of_the_week_status()
                # await asyncio.sleep(0.1)
                device_data[ATTR_VOLUME_LEVEL] = await device.get_volume_level()
                await asyncio.sleep(0.1)
                device_data[ATTR_TIME_MODE] = await device.get_time_mode()
                await asyncio.sleep(0.1)

                # device_data[ATTR_ALARMS] = await device.get_all_alarms()
                # await asyncio.sleep(0.1)

                # device_data[ATTR_WEATHER] = await device.get_weather_configuration(
                #     device
                # )
                # await asyncio.sleep(0.1)
                device_data[ATTR_WIFI] = await device.get_wifi_status()
                await asyncio.sleep(0.1)

                device_data[ATTR_COLON_BLINK] = await device.get_colon_blink_mode()
                await asyncio.sleep(0.1)

                device_data[ATTR_USE_COLON] = await device.get_use_colon_mode()
                await asyncio.sleep(0.1)

                device_data[
                    ATTR_USE_LEADING_ZERO
                ] = await device.get_use_leading_zero_mode()
                await asyncio.sleep(0.1)

                device_data[
                    ATTR_DISPLAY_SECONDS
                ] = await device.get_display_seconds_mode()
                await asyncio.sleep(0.1)

                device_data[
                    ATTR_ALEXA_USE_ASCENDING_ALARMS
                ] = await device.get_alexa_ascending_alarms_mode()
                await asyncio.sleep(0.1)

                device_data[
                    ATTR_ALEXA_TAPTALK_TONE
                ] = await device.get_is_alexa_tap_to_talk_tone_enabled()
                await asyncio.sleep(0.1)

                device_data[
                    ATTR_ALEXA_WAKEWORD_TONE
                ] = await device.get_is_alexa_wake_word_tone_enabled()
                await asyncio.sleep(0.1)

                preset = await device.get_sound_preset()
                if preset == "PRESET1":
                    device_data[ATTR_SOUND_PRESET] = "Preset 1 Balanced"
                elif preset == "PRESET2":
                    device_data[ATTR_SOUND_PRESET] = "Preset 2 Bass Boost"
                elif preset == "PRESET3":
                    device_data[ATTR_SOUND_PRESET] = "Preset 3 Treble Boost"
                elif preset == "PRESET4":
                    device_data[ATTR_SOUND_PRESET] = "Preset 4 Mids Boost"
                elif preset == "PRESET5":
                    device_data[ATTR_SOUND_PRESET] = "Preset 5 Untuned"

                await asyncio.sleep(0.1)
                # _LOGGER.warning("Before api.get_sound_preset_mode")
                device_data[
                    ATTR_SOUND_PRESET_MODE
                ] = await device.get_sound_preset_mode()
                await asyncio.sleep(0.1)

                # _LOGGER.warning("Before api.get_weather_status")
                device_data[ATTR_WEATHER] = await device.get_weather_configuration()
                # device_data[ATTR_WEATHER_ON] = True
                await asyncio.sleep(0.1)

                # device_data[ATTR_WEATHER_MODE] = 15
                await asyncio.sleep(0.1)
                # _LOGGER.warning("Before api.get_lightsensor_value")
                device_data[
                    ATTR_LIGHTSENSOR_VALUE
                ] = await device.get_light_sensor_value()
                await asyncio.sleep(0.1)

                device_data[
                    ATTR_DAYNIGHTMODE_VALUE
                ] = await device.get_day_night_mode_status()
                await asyncio.sleep(0.1)

                device_data[ATTR_TIMEOFFSET] = await device.get_offset()
                await asyncio.sleep(0.1)
                # _LOGGER.warning("Before api.get_timezone")
                device_data[ATTR_TIMEZONE] = await device.get_timezone()
                _LOGGER.warning("DONE loop for device %s", device)

        except Exception as exception:
            _LOGGER.debug("%s: %s", type(exception), exception)
            raise UpdateFailed() from exception
        # _LOGGER.warning("sandman_doppler Completed _async_update_data")
        return data


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    unloaded = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
            ]
        )
    )
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
