"""The Sandman Doppler services module."""
from __future__ import annotations

from datetime import timedelta
import logging

from doppyler.client import DopplerClient
from doppyler.model.alarm import Alarm, AlarmDict, AlarmSource
from doppyler.model.doppler import Doppler
from doppyler.model.light_bar import LightbarDisplayDict, LightbarDisplayEffect
from doppyler.model.main_display_text import MainDisplayText, MainDisplayTextDict
from doppyler.model.mini_display_number import MiniDisplayNumber, MiniDisplayNumberDict
from homeassistant.const import (
    ATTR_AREA_ID,
    ATTR_DEVICE_ID,
    ATTR_ENTITY_ID,
    ATTR_LOCATION,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.service import ServiceCall

from .const import DOMAIN

SCAN_INTERVAL = timedelta(seconds=60)

_LOGGER = logging.getLogger(__name__)


class DopplerServices:
    """Class to represent Sandman Doppler integration services."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: DopplerClient,
        ent_reg: er.EntityRegistry,
        dev_reg: dr.DeviceRegistry,
    ) -> None:
        """Initialize services."""
        self.hass = hass
        self.ent_reg = ent_reg
        self.dev_reg = dev_reg
        self.client = client

    @callback
    def async_register(self):
        """Register services."""
        self.hass.services.async_register(
            DOMAIN, "set_weather_location", self.handle_set_weather_location_svc
        )
        self.hass.services.async_register(
            DOMAIN, "add_alarm", self.handle_add_alarm_svc
        )
        self.hass.services.async_register(
            DOMAIN, "delete_alarm", self.handle_delete_alarm_svc
        )
        self.hass.services.async_register(
            DOMAIN, "set_main_display_text", self.handle_set_main_display_svc
        )
        self.hass.services.async_register(
            DOMAIN, "set_mini_display_number", self.handle_set_mini_display_svc
        )
        self.hass.services.async_register(
            DOMAIN, "set_light_bar_color", self.handle_set_light_bar_color_svc
        )
        self.hass.services.async_register(
            DOMAIN, "set_each_light_bar_color", self.handle_set_each_light_bar_color_svc
        )
        self.hass.services.async_register(
            DOMAIN, "set_light_bar_blink", self.handle_set_light_bar_blink_svc
        )
        self.hass.services.async_register(
            DOMAIN, "set_light_bar_pulse", self.handle_set_light_bar_pulse_svc
        )
        self.hass.services.async_register(
            DOMAIN, "set_light_bar_comet", self.handle_set_light_bar_comet_svc
        )
        self.hass.services.async_register(
            DOMAIN, "set_light_bar_sweep", self.handle_set_light_bar_sweep_svc
        )

    def get_dopplers_from_svc_targets(self, call: ServiceCall) -> set[Doppler]:
        """Get dopplers from service targets."""
        dopplers: set[Doppler] = set()
        device_ids: set[str] = set()
        device_ids.update(call.data.get(ATTR_DEVICE_ID, []))
        device_ids.update(
            {
                entity_entry.device_id
                for entity_id in call.data.get(ATTR_ENTITY_ID, [])
                if (entity_entry := self.ent_reg.async_get(entity_id))
                and entity_entry.device_id
            }
        )
        device_ids.update(
            {
                dev.id
                for area_id in call.data.get(ATTR_AREA_ID, [])
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
            dopplers.add(self.client.devices[identifier[1]])

        return dopplers

    async def handle_set_weather_location_svc(self, call: ServiceCall) -> None:
        for device in self.get_dopplers_from_svc_targets(call):
            await device.set_weather_configuration(location=call.data[ATTR_LOCATION])

    async def handle_add_alarm_svc(self, call: ServiceCall) -> None:
        if "repeat" in call.data:
            r = call.data["repeat"]
        else:
            r = ""

        hr, min, *_ = call.data["time"].split(":")
        alarmdict = AlarmDict(
            id=int(call.data["id"]),
            name=call.data["name"],
            time_hr=int(hr),
            time_min=int(min),
            repeat=r,
            color={
                "red": int(call.data["color"][0]),
                "green": int(call.data["color"][1]),
                "blue": int(call.data["color"][2]),
            },
            volume=int(call.data["volume"]),
            status=call.data["status"],
            src=AlarmSource.APP,
            sound=call.data["sound"],
        )
        for device in self.get_dopplers_from_svc_targets(call):
            try:
                result = await device.add_alarm(Alarm.from_dict(alarmdict))
            except Exception as err:
                raise HomeAssistantError from err
            _LOGGER.warning(f"alarm result was {result}")

    async def handle_delete_alarm_svc(self, call: ServiceCall) -> None:
        for device in self.get_dopplers_from_svc_targets(call):
            await device.delete_alarm(int(call.data["id"]))

    async def handle_set_main_display_svc(self, call: ServiceCall) -> None:
        # regex for accepted characters: (?![kmwv])[a-z0-9 \_\-]+
        _LOGGER.warning(f"Called handle_set_main_display service")
        mdt_dict = MainDisplayTextDict(
            {
                "text": str(call.data["text"]),
                "duration": int(timedelta(**call.data["duration"]).total_seconds()),
                "speed": int(call.data["speed"]),
                "color": [
                    int(call.data["color"][0]),
                    int(call.data["color"][1]),
                    int(call.data["color"][2]),
                ],
            }
        )

        for device in self.get_dopplers_from_svc_targets(call):
            await device.set_main_display_text(MainDisplayText.from_dict(mdt_dict))

    async def handle_set_mini_display_svc(self, call: ServiceCall) -> None:
        _LOGGER.warning(f"Called handle_display_num_mini service")
        mdn_dict = MiniDisplayNumberDict(
            {
                "num": int(call.data["number"]),
                "duration": int(timedelta(**call.data["duration"]).total_seconds()),
                "color": [
                    int(call.data["color"][0]),
                    int(call.data["color"][1]),
                    int(call.data["color"][2]),
                ],
            }
        )

        for device in self.get_dopplers_from_svc_targets(call):
            await device.set_mini_display_number(MiniDisplayNumber.from_dict(mdn_dict))

    async def handle_set_light_bar_color_svc(self, call: ServiceCall) -> None:
        _LOGGER.warning(f"data was {call.data}")
        _LOGGER.warning(f"Called handle_set_light_bar_color service")
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
        for device in self.get_dopplers_from_svc_targets(call):
            retval = await device.set_light_bar_effect(
                LightbarDisplayEffect.from_dict(lbde_dict)
            )
        _LOGGER.warning(f"retval={retval.to_dict()}")

    async def handle_set_each_light_bar_color_svc(self, call: ServiceCall) -> None:
        _LOGGER.warning(f"data was {call.data}")
        _LOGGER.warning(f"Called handle_set_light_bar_color service")
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
        for device in self.get_dopplers_from_svc_targets(call):
            retval = await device.set_light_bar_effect(
                LightbarDisplayEffect.from_dict(lbde_dict)
            )
        _LOGGER.warning(f"retval={retval.to_dict()}")

    async def handle_set_light_bar_blink_svc(self, call: ServiceCall) -> None:
        _LOGGER.warning(f"data was {call.data}")
        _LOGGER.warning(f"Called handle_set_light_bar_color service")
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
        for device in self.get_dopplers_from_svc_targets(call):
            retval = await device.set_light_bar_effect(
                LightbarDisplayEffect.from_dict(lbde_dict)
            )
        _LOGGER.warning(f"retval={retval.to_dict()}")

    async def handle_set_light_bar_pulse_svc(self, call: ServiceCall) -> None:
        _LOGGER.warning(f"data was {call.data}")
        _LOGGER.warning(f"Called handle_set_light_bar_pulse service")
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
        for device in self.get_dopplers_from_svc_targets(call):
            retval = await device.set_light_bar_effect(
                LightbarDisplayEffect.from_dict(lbde_dict)
            )
        _LOGGER.warning(f"retval={retval.to_dict()}")

    async def handle_set_light_bar_comet_svc(self, call: ServiceCall) -> None:
        _LOGGER.warning(f"data was {call.data}")
        _LOGGER.warning(f"Called handle_set_light_bar_pulse service")
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
        for device in self.get_dopplers_from_svc_targets(call):
            retval = await device.set_light_bar_effect(
                LightbarDisplayEffect.from_dict(lbde_dict)
            )
        _LOGGER.warning(f"retval={retval.to_dict()}")

    async def handle_set_light_bar_sweep_svc(self, call: ServiceCall) -> None:
        _LOGGER.warning(f"data was {call.data}")
        _LOGGER.warning(f"Called handle_set_light_bar_sweep service")
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
        for device in self.get_dopplers_from_svc_targets(call):
            retval = await device.set_light_bar_effect(
                LightbarDisplayEffect.from_dict(lbde_dict)
            )
        _LOGGER.warning(f"retval={retval.to_dict()}")
