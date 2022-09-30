"""The Sandman Doppler services module."""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import timedelta
from functools import wraps
import logging
from typing import Any

from doppyler.client import DopplerClient
from doppyler.exceptions import DopplerException
from doppyler.model.alarm import Alarm, AlarmSource, RepeatDayOfWeek
from doppyler.model.color import Color
from doppyler.model.doppler import Doppler
from doppyler.model.light_bar import LightbarDisplayDict, LightbarDisplayEffect
from doppyler.model.main_display_text import MainDisplayText
from doppyler.model.mini_display_number import MiniDisplayNumber
from homeassistant.const import (
    ATTR_AREA_ID,
    ATTR_DEVICE_ID,
    ATTR_ENTITY_ID,
    ATTR_TIME,
    CONF_ENABLED,
    CONF_ID,
    CONF_LOCATION,
    CONF_NAME,
    CONF_REPEAT,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.helpers.service import ServiceCall
import voluptuous as vol

from .const import DOMAIN

SCAN_INTERVAL = timedelta(seconds=60)

_LOGGER = logging.getLogger(__name__)

ATTR_COLOR = "color"
ATTR_DEVICES = "devices"
ATTR_DIRECTION = "direction"
ATTR_DURATION = "duration"
ATTR_ENABLED = CONF_ENABLED
ATTR_GAP = "gap"
ATTR_ID = CONF_ID
ATTR_LOCATION = CONF_LOCATION
ATTR_NAME = CONF_NAME
ATTR_NUMBER = "number"
ATTR_RAINBOW = "rainbow"
ATTR_REPEAT = CONF_REPEAT
ATTR_SIZE = "size"
ATTR_SOUND = "sound"
ATTR_SPARKLE = "sparkle"
ATTR_SPEED = "speed"
ATTR_TEXT = "text"
ATTR_VOLUME = "volume"

COLOR_SCHEMA = vol.All(
    [vol.All(vol.Coerce(int), vol.Range(0, 255))],
    vol.Length(3, 3),
    lambda x: Color.from_list(x),
)
BASE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_AREA_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
    }
)


def async_service_wrapper(orig_func: Callable) -> Callable:
    """Decorate service function to get devices and handle errors."""

    @wraps(orig_func)
    async def async_service_wrapper_func(self, call: ServiceCall) -> None:
        """Grab device list to reduce repeat code and handle exceptions."""
        try:
            await orig_func(self, call, call.data[ATTR_DEVICES])
        except DopplerException as err:
            raise HomeAssistantError from err

    return async_service_wrapper_func


async def call_doppyler_api_across_devices(
    devices: set[Doppler], func_name: str, *args, **kwargs
) -> None:
    """Call Doppyler API across all devices."""
    results = await asyncio.gather(
        *(getattr(device, func_name)(*args, **kwargs) for device in devices),
        return_exceptions=True,
    )
    if errors := (
        tup for tup in zip(devices, results) if isinstance(tup[1], Exception)
    ):
        lines = (
            f"{len(errors)} error(s):",
            *(
                f"{device} - {type(error).__name__}: {error}"
                for device, error in errors
            ),
        )
        raise HomeAssistantError("\n".join(lines))


class DopplerServices:
    """Class to represent Sandman Doppler integration services."""

    def __init__(
        self,
        hass: HomeAssistant,
        ent_reg: er.EntityRegistry,
        dev_reg: dr.DeviceRegistry,
        client: DopplerClient,
    ) -> None:
        """Initialize services."""
        self.hass = hass
        self.ent_reg = ent_reg
        self.dev_reg = dev_reg
        self.client = client

    @callback
    def get_dopplers_from_targets(self, data: dict[str, Any]) -> dict[str, Any]:
        """Get dopplers from service targets."""
        devices: set[Doppler] = set()
        device_ids: set[str] = set()
        device_ids.update(data.get(ATTR_DEVICE_ID, []))
        device_ids.update(
            {
                entity_entry.device_id
                for entity_id in data.get(ATTR_ENTITY_ID, [])
                if (entity_entry := self.ent_reg.async_get(entity_id))
                and entity_entry.device_id
            }
        )
        device_ids.update(
            {
                dev.id
                for area_id in data.get(ATTR_AREA_ID, [])
                for dev in dr.async_entries_for_area(self.dev_reg, area_id)
            }
        )

        for device_id in device_ids:
            if not (device_entry := self.dev_reg.async_get(device_id)):
                continue
            identifier = next(id for id in device_entry.identifiers)
            if identifier[0] != DOMAIN:
                _LOGGER.warning(
                    "Skipping device %s for service call because it is not a supported "
                    "Sandman Doppler device"
                )
                continue
            devices.add(self.client.devices[identifier[1]])

        if not devices:
            raise vol.Invalid("No devices found in given targets!")

        data[ATTR_DEVICES] = devices
        return data

    def _expand_schema(
        self,
        schema: dict[vol.Marker, Any],
        extra: vol.ALLOW_EXTRA | vol.REMOVE_EXTRA = vol.REMOVE_EXTRA,
    ) -> vol.Schema:
        """Get expanded schema from service specific schema."""
        return vol.All(
            BASE_SCHEMA.extend(schema, extra=extra),
            cv.has_at_least_one_key(ATTR_DEVICE_ID, ATTR_ENTITY_ID, ATTR_AREA_ID),
            self.get_dopplers_from_targets,
        )

    @callback
    def async_register(self):
        """Register services."""
        self.hass.services.async_register(
            DOMAIN,
            "set_weather_location",
            self.handle_set_weather_location,
            schema=self._expand_schema({vol.Required(ATTR_LOCATION): cv.string}),
        )

        self.hass.services.async_register(
            DOMAIN,
            "add_alarm",
            self.handle_add_alarm,
            schema=self._expand_schema(
                {
                    vol.Required(ATTR_ID): vol.Coerce(int),
                    vol.Required(ATTR_NAME): cv.string,
                    vol.Required(ATTR_TIME): cv.time,
                    vol.Required(ATTR_REPEAT, default=[]): vol.All(
                        cv.ensure_list, [vol.Coerce(RepeatDayOfWeek)]
                    ),
                    vol.Required(ATTR_COLOR): COLOR_SCHEMA,
                    vol.Required(ATTR_VOLUME): vol.All(
                        vol.Coerce(int), vol.Range(1, 100)
                    ),
                    vol.Required(ATTR_ENABLED): cv.boolean,
                    vol.Required(ATTR_SOUND): cv.string,
                }
            ),
        )

        self.hass.services.async_register(
            DOMAIN,
            "delete_alarm",
            self.handle_delete_alarm,
            schema=self._expand_schema({vol.Required(ATTR_ID): vol.Coerce(int)}),
        )

        self.hass.services.async_register(
            DOMAIN,
            "set_main_display_text",
            self.handle_set_main_display,
            schema=self._expand_schema(
                {
                    vol.Required(ATTR_TEXT): vol.All(
                        cv.string, cv.matches_regex(r"(?![kmwv])[a-z0-9 \_\-]+")
                    ),
                    vol.Required(ATTR_SPEED): vol.Coerce(int),
                    vol.Required(ATTR_DURATION): cv.time_period,
                    vol.Required(ATTR_COLOR): COLOR_SCHEMA,
                }
            ),
        )

        self.hass.services.async_register(
            DOMAIN,
            "set_mini_display_number",
            self.handle_set_mini_display,
            schema=self._expand_schema(
                {
                    vol.Optional(ATTR_NUMBER): vol.Coerce(int),
                    vol.Optional(ATTR_DURATION): cv.time_period,
                    vol.Optional(ATTR_COLOR): COLOR_SCHEMA,
                }
            ),
        )

        self.hass.services.async_register(
            DOMAIN,
            "set_light_bar_color",
            self.handle_set_light_bar_color,
            schema=self._expand_schema({}, extra=vol.ALLOW_EXTRA),
        )

        self.hass.services.async_register(
            DOMAIN,
            "set_each_light_bar_color",
            self.handle_set_each_light_bar_color,
            schema=self._expand_schema({}, extra=vol.ALLOW_EXTRA),
        )

        self.hass.services.async_register(
            DOMAIN,
            "set_light_bar_blink",
            self.handle_set_light_bar_blink,
            schema=self._expand_schema({}, extra=vol.ALLOW_EXTRA),
        )

        self.hass.services.async_register(
            DOMAIN,
            "set_light_bar_pulse",
            self.handle_set_light_bar_pulse,
            schema=self._expand_schema({}, extra=vol.ALLOW_EXTRA),
        )

        self.hass.services.async_register(
            DOMAIN,
            "set_light_bar_comet",
            self.handle_set_light_bar_comet,
            schema=self._expand_schema({}, extra=vol.ALLOW_EXTRA),
        )

        self.hass.services.async_register(
            DOMAIN,
            "set_light_bar_sweep",
            self.handle_set_light_bar_sweep,
            schema=self._expand_schema({}, extra=vol.ALLOW_EXTRA),
        )

    @async_service_wrapper
    async def handle_set_weather_location(
        self, call: ServiceCall, devices: set[Doppler]
    ) -> None:
        _LOGGER.warning(f"Called set_weather_location service")
        call_doppyler_api_across_devices(
            devices, "set_weather_configuration", location=call.data[ATTR_LOCATION]
        )

    @async_service_wrapper
    async def handle_add_alarm(self, call: ServiceCall, devices: set[Doppler]) -> None:
        _LOGGER.warning(f"Called add_alarm service")
        alarm = Alarm(
            id=call.data[ATTR_ID],
            name=call.data[ATTR_NAME],
            alarm_time=call.data[ATTR_TIME],
            repeat=call.data[ATTR_REPEAT],
            color=call.data[ATTR_COLOR],
            volume=call.data[ATTR_VOLUME],
            status=call.data[ATTR_ENABLED],
            src=AlarmSource.APP,
            sound=call.data[ATTR_SOUND],
        )
        call_doppyler_api_across_devices(devices, "add_alarm", alarm)

    @async_service_wrapper
    async def handle_delete_alarm(
        self, call: ServiceCall, devices: set[Doppler]
    ) -> None:
        _LOGGER.warning(f"Called delete_alarm service")
        call_doppyler_api_across_devices(devices, "delete_alarm", call.data[ATTR_ID])

    @async_service_wrapper
    async def handle_set_main_display(
        self, call: ServiceCall, devices: set[Doppler]
    ) -> None:
        _LOGGER.warning(f"Called set_main_display service")
        mdt = MainDisplayText(
            text=call.data[ATTR_TEXT],
            duration=call.data[ATTR_DURATION],
            speed=call.data[ATTR_SPEED],
            color=call.data[ATTR_COLOR],
        )
        call_doppyler_api_across_devices(devices, "set_main_display_text", mdt)

    @async_service_wrapper
    async def handle_set_mini_display(
        self, call: ServiceCall, devices: set[Doppler]
    ) -> None:
        _LOGGER.warning(f"Called display_num_mini service")
        mdn = MiniDisplayNumber(
            number=call.data[ATTR_NUMBER],
            duration=call.data[ATTR_DURATION],
            color=call.data[ATTR_COLOR],
        )
        call_doppyler_api_across_devices(devices, "set_mini_display_number", mdn)

    @async_service_wrapper
    async def handle_set_light_bar_color(
        self, call: ServiceCall, devices: set[Doppler]
    ) -> None:
        _LOGGER.warning(f"data was {call.data}")
        _LOGGER.warning(f"Called set_light_bar_color service")
        color_list = [
            [color[0], color[1], color[2]]
            for i in range(12)
            if (color := call.data.get(f"color_{i + 1}")) is not None
        ]
        s = call.data.get("sparkle")
        r = call.data.get("rainbow")

        attributes_dict = {}
        attributes_dict["display"] = "set"
        if s is not None:
            attributes_dict["sparkle"] = f"{s}"
        if r is not None:
            if r is True:
                attributes_dict["rainbow"] = str("true")
            else:
                attributes_dict["rainbow"] = str("false")

        lbde_dict = LightbarDisplayDict(
            {
                "colors": color_list,
                "duration": int(timedelta(**call.data["duration"]).total_seconds()),
                "speed": int(call.data["speed"]),
                "attributes": attributes_dict,
            }
        )
        _LOGGER.warning(f"lbde_dict={lbde_dict}")
        call_doppyler_api_across_devices(
            devices, "set_light_bar_effect", LightbarDisplayEffect.from_dict(lbde_dict)
        )

    @async_service_wrapper
    async def handle_set_each_light_bar_color(
        self, call: ServiceCall, devices: set[Doppler]
    ) -> None:
        _LOGGER.warning(f"data was {call.data}")
        _LOGGER.warning(f"Called set_each_light_bar_color service")
        color_list = [
            [color[0], color[1], color[2]]
            for i in range(29)
            if (color := call.data.get(f"color_{i + 1}")) is not None
        ]
        s = call.data.get("sparkle")
        r = call.data.get("rainbow")

        attributes_dict = {}
        attributes_dict["display"] = "set-each"
        if s is not None:
            attributes_dict["sparkle"] = f"{s}"
        if r is not None:
            if r is True:
                attributes_dict["rainbow"] = str("true")
            else:
                attributes_dict["rainbow"] = str("false")

        lbde_dict = LightbarDisplayDict(
            {
                "colors": color_list,
                "duration": int(timedelta(**call.data["duration"]).total_seconds()),
                "speed": 0,
                "attributes": attributes_dict,
            }
        )
        _LOGGER.warning(f"lbde_dict={lbde_dict}")
        call_doppyler_api_across_devices(
            devices, "set_light_bar_effect", LightbarDisplayEffect.from_dict(lbde_dict)
        )

    @async_service_wrapper
    async def handle_set_light_bar_blink(
        self, call: ServiceCall, devices: set[Doppler]
    ) -> None:
        _LOGGER.warning(f"data was {call.data}")
        _LOGGER.warning(f"Called set_light_bar_color service")
        color_list = [
            [color[0], color[1], color[2]]
            for i in range(12)
            if (color := call.data.get(f"color_{i + 1}")) is not None
        ]
        s = call.data.get("sparkle")
        r = call.data.get("rainbow")
        sp = call.data.get("speed")

        attributes_dict = {}
        attributes_dict["display"] = "blink"
        if s is not None:
            attributes_dict["sparkle"] = f"{s}"
        if r is not None:
            if r == True:
                attributes_dict["rainbow"] = str("true")
            else:
                attributes_dict["rainbow"] = str("false")

        lbde_dict = LightbarDisplayDict(
            {
                "colors": color_list,
                "duration": int(timedelta(**call.data["duration"]).total_seconds()),
                "speed": int(call.data["speed"]),
                "attributes": attributes_dict,
            }
        )

        _LOGGER.warning(f"lbde_dict={lbde_dict}")
        call_doppyler_api_across_devices(
            devices, "set_light_bar_effect", LightbarDisplayEffect.from_dict(lbde_dict)
        )

    @async_service_wrapper
    async def handle_set_light_bar_pulse(
        self, call: ServiceCall, devices: set[Doppler]
    ) -> None:
        _LOGGER.warning(f"data was {call.data}")
        _LOGGER.warning(f"Called set_light_bar_pulse service")
        color_list = [
            [color[0], color[1], color[2]]
            for i in range(12)
            if (color := call.data.get(f"color_{i + 1}")) is not None
        ]
        s = call.data.get("sparkle")
        r = call.data.get("rainbow")
        sp = call.data.get("speed")
        gp = call.data.get("gap")

        attributes_dict = {}
        attributes_dict["display"] = "pulse"
        if gp is not None:
            attributes_dict["gap"] = f"{gp}"
        if s is not None:
            attributes_dict["sparkle"] = f"{s}"
        if r is not None:
            if r == True:
                attributes_dict["rainbow"] = str("true")
            else:
                attributes_dict["rainbow"] = str("false")

        lbde_dict = LightbarDisplayDict(
            {
                "colors": color_list,
                "duration": int(timedelta(**call.data["duration"]).total_seconds()),
                "speed": int(call.data["speed"]),
                "attributes": attributes_dict,
            }
        )

        _LOGGER.warning(f"lbde_dict={lbde_dict}")
        call_doppyler_api_across_devices(
            devices, "set_light_bar_effect", LightbarDisplayEffect.from_dict(lbde_dict)
        )

    @async_service_wrapper
    async def handle_set_light_bar_comet(
        self, call: ServiceCall, devices: set[Doppler]
    ) -> None:
        _LOGGER.warning(f"data was {call.data}")
        _LOGGER.warning(f"Called set_light_bar_pulse service")
        color_list = [
            [color[0], color[1], color[2]]
            for i in range(12)
            if (color := call.data.get(f"color_{i + 1}")) is not None
        ]
        s = call.data.get("sparkle")
        r = call.data.get("rainbow")
        sz = call.data.get("size")
        direct = call.data.get("direction")

        attributes_dict = {}
        attributes_dict["display"] = "comet"
        if sz is not None:
            attributes_dict["size"] = f"{sz}"
        else:
            attributes_dict["size"] = f"10"
        if direct is not None:
            attributes_dict["direction"] = f"{direct}"
        else:
            attributes_dict["direction"] = "right"
        if s is not None:
            attributes_dict["sparkle"] = f"{s}"
        if r is not None:
            if r == True:
                attributes_dict["rainbow"] = str("true")
            else:
                attributes_dict["rainbow"] = str("false")

        lbde_dict = LightbarDisplayDict(
            {
                "colors": color_list,
                "duration": int(timedelta(**call.data["duration"]).total_seconds()),
                "speed": int(call.data["speed"]),
                "attributes": attributes_dict,
            }
        )

        _LOGGER.warning(f"lbde_dict={lbde_dict}")
        call_doppyler_api_across_devices(
            devices, "set_light_bar_effect", LightbarDisplayEffect.from_dict(lbde_dict)
        )

    @async_service_wrapper
    async def handle_set_light_bar_sweep(
        self, call: ServiceCall, devices: set[Doppler]
    ) -> None:
        _LOGGER.warning(f"data was {call.data}")
        _LOGGER.warning(f"Called set_light_bar_sweep service")
        color_list = [
            [color[0], color[1], color[2]]
            for i in range(12)
            if (color := call.data.get(f"color_{i + 1}")) is not None
        ]
        s = call.data.get("sparkle")
        r = call.data.get("rainbow")
        sp = call.data.get("speed")
        gp = call.data.get("gap")
        sz = call.data.get("size")
        direct = call.data.get("direction")

        attributes_dict = {}
        attributes_dict["display"] = "sweep"
        if gp is not None:
            attributes_dict["gap"] = f"{gp}"
        if s is not None:
            attributes_dict["sparkle"] = f"{s}"
        if sz is not None:
            attributes_dict["size"] = f"{sz}"
        else:
            attributes_dict["size"] = "10"
        if direct is not None:
            attributes_dict["direction"] = f"{direct}"
        else:
            attributes_dict["direction"] = "right"
        if r is not None:
            if r is True:
                attributes_dict["rainbow"] = str("true")
            else:
                attributes_dict["rainbow"] = str("false")

        lbde_dict = LightbarDisplayDict(
            {
                "colors": color_list,
                "duration": int(timedelta(**call.data["duration"]).total_seconds()),
                "speed": int(call.data["speed"]),
                "attributes": attributes_dict,
            }
        )

        _LOGGER.warning(f"lbde_dict={lbde_dict}")
        call_doppyler_api_across_devices(
            devices, "set_light_bar_effect", LightbarDisplayEffect.from_dict(lbde_dict)
        )
