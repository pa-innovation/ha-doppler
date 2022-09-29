"""The Sandman Doppler integration."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from doppyler.client import DopplerClient
from doppyler.exceptions import DopplerException
from doppyler.model.alarm import Alarm, AlarmDict, AlarmSource
from doppyler.model.doppler import Doppler
from doppyler.model.light_bar import LightbarDisplayDict, LightbarDisplayEffect
from doppyler.model.main_display_text import MainDisplayText, MainDisplayTextDict
from doppyler.model.mini_display_number import MiniDisplayNumber, MiniDisplayNumberDict
from homeassistant.config_entries import ConfigEntry, ConfigEntryNotReady
from homeassistant.const import (
    ATTR_AREA_ID,
    ATTR_DEVICE_ID,
    ATTR_ENTITY_ID,
    CONF_EMAIL,
    CONF_PASSWORD,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.service import ServiceCall
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, PLATFORMS

SCAN_INTERVAL = timedelta(seconds=60)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up config entry."""
    hass.data.setdefault(DOMAIN, {}).setdefault(entry.entry_id, {})

    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]

    session = async_get_clientsession(hass)
    client = DopplerClient(email, password, client_session=session, local_control=False)

    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    @callback
    def async_on_device_added(device: Doppler) -> None:
        """Handle device added."""
        _LOGGER.debug("Device added: %s", device)
        hass.data[DOMAIN][entry.entry_id][
            device.dsn
        ] = coordinator = DopplerDataUpdateCoordinator(hass, entry, client, device)
        dev_reg.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, device.dsn)},
            manufacturer=device.device_info.manufacturer,
            model=device.device_info.model_number,
            sw_version=device.device_info.software_version,
            hw_version=device.device_info.firmware_version,
            name=device.name,
        )
        hass.async_create_task(coordinator.async_refresh())

    @callback
    def async_on_device_removed(device: Doppler) -> None:
        """Handle device removed."""
        _LOGGER.debug("Device removed: %s", device)
        dev_entry = dev_reg.async_get_device({(DOMAIN, device.dsn)})
        assert dev_entry
        dev_reg.async_remove_device(dev_entry.id)
        hass.data[DOMAIN][entry.entry_id].pop(device.dsn)

    entry.async_on_unload(client.on_device_added(async_on_device_added))
    entry.async_on_unload(client.on_device_removed(async_on_device_removed))

    try:
        await client.get_devices()
    except DopplerException as err:
        raise ConfigEntryNotReady from err
    entry.async_on_unload(
        async_track_time_interval(
            hass, lambda _: client.get_devices(), timedelta(minutes=5)
        )
    )

    def get_dopplers_from_svc_targets(call: ServiceCall) -> set[Doppler]:
        """Get dopplers from service targets."""
        dopplers: set[Doppler] = set()
        device_ids: set[str] = set()
        device_ids.update(call.data.get(ATTR_DEVICE_ID, []))
        device_ids.update(
            {
                entity_entry.device_id
                for entity_id in call.data.get(ATTR_ENTITY_ID, [])
                if (entity_entry := ent_reg.async_get(entity_id))
                and entity_entry.device_id
            }
        )
        device_ids.update(
            {
                dev.id
                for area_id in call.data.get(ATTR_AREA_ID, [])
                for dev in dr.async_entries_for_area(dev_reg, area_id)
            }
        )

        for device_id in device_ids:
            if not (device_entry := dev_reg.async_get(device_id)):
                continue
            identifier = next(id for id in device_entry.identifiers)
            if identifier[0] != DOMAIN:
                _LOGGER.warning(
                    "Skipping device %s for service call because it is not a supported "
                    "Sandman Doppler device"
                )
                continue
            dopplers.add(client.devices[identifier[1]])

        return dopplers

    async def handle_add_alarm_svc(call: ServiceCall) -> None:
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
        for device in get_dopplers_from_svc_targets(call):
            try:
                result = await device.add_alarm(Alarm.from_dict(alarmdict))
            except Exception as err:
                raise HomeAssistantError from err
            _LOGGER.warning(f"alarm result was {result}")

    async def handle_delete_alarm_svc(call: ServiceCall) -> None:
        for device in get_dopplers_from_svc_targets(call):
            await device.delete_alarm(int(call.data["id"]))

    async def handle_set_main_display_svc(call: ServiceCall) -> None:

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

        for device in get_dopplers_from_svc_targets(call):
            await device.set_main_display_text(MainDisplayText.from_dict(mdt_dict))

    async def handle_set_mini_display_svc(call: ServiceCall) -> None:
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

        for device in get_dopplers_from_svc_targets(call):
            await device.set_mini_display_number(MiniDisplayNumber.from_dict(mdn_dict))

    async def handle_set_light_bar_color_svc(call: ServiceCall) -> None:
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
        for device in get_dopplers_from_svc_targets(call):
            retval = await device.set_light_bar_effect(
                LightbarDisplayEffect.from_dict(lbde_dict)
            )
        _LOGGER.warning(f"retval={retval.to_dict()}")

    async def handle_set_each_light_bar_color_svc(call: ServiceCall) -> None:
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
        for device in get_dopplers_from_svc_targets(call):
            retval = await device.set_light_bar_effect(
                LightbarDisplayEffect.from_dict(lbde_dict)
            )
        _LOGGER.warning(f"retval={retval.to_dict()}")

    async def handle_set_light_bar_blink_svc(call: ServiceCall) -> None:
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
        for device in get_dopplers_from_svc_targets(call):
            retval = await device.set_light_bar_effect(
                LightbarDisplayEffect.from_dict(lbde_dict)
            )
        _LOGGER.warning(f"retval={retval.to_dict()}")

    async def handle_set_light_bar_pulse_svc(call: ServiceCall) -> None:
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
        for device in get_dopplers_from_svc_targets(call):
            retval = await device.set_light_bar_effect(
                LightbarDisplayEffect.from_dict(lbde_dict)
            )
        _LOGGER.warning(f"retval={retval.to_dict()}")

    async def handle_set_light_bar_comet_svc(call: ServiceCall) -> None:
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
        for device in get_dopplers_from_svc_targets(call):
            retval = await device.set_light_bar_effect(
                LightbarDisplayEffect.from_dict(lbde_dict)
            )
        _LOGGER.warning(f"retval={retval.to_dict()}")

    async def handle_set_light_bar_sweep_svc(call: ServiceCall) -> None:
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
        for device in get_dopplers_from_svc_targets(call):
            retval = await device.set_light_bar_effect(
                LightbarDisplayEffect.from_dict(lbde_dict)
            )
        _LOGGER.warning(f"retval={retval.to_dict()}")

    hass.services.async_register(
        DOMAIN, "add_alarm", handle_add_alarm_svc
    )
    hass.services.async_register(DOMAIN, "delete_alarm", handle_delete_alarm_svc)
    hass.services.async_register(
        DOMAIN, "set_main_display_text", handle_set_main_display_svc
    )
    hass.services.async_register(
        DOMAIN, "set_mini_display_number", handle_set_mini_display_svc
    )
    hass.services.async_register(
        DOMAIN, "set_light_bar_color", handle_set_light_bar_color_svc
    )
    hass.services.async_register(
        DOMAIN, "set_each_light_bar_color", handle_set_each_light_bar_color_svc
    )
    hass.services.async_register(
        DOMAIN, "set_light_bar_blink", handle_set_light_bar_blink_svc
    )
    hass.services.async_register(
        DOMAIN, "set_light_bar_pulse", handle_set_light_bar_pulse_svc
    )
    hass.services.async_register(
        DOMAIN, "set_light_bar_comet", handle_set_light_bar_comet_svc
    )
    hass.services.async_register(
        DOMAIN, "set_light_bar_sweep", handle_set_light_bar_sweep_svc
    )

    return True


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


class DopplerDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching data from the API."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: DopplerClient,
        device: Doppler,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass, _LOGGER, name=f"{DOMAIN}_{device.dsn}", update_interval=SCAN_INTERVAL
        )
        self.data: dict[str, Any] = {}
        self.api = client
        self.device = device
        self._entry = entry
        self._entities_created = False

    async def _reschedule_refresh(self) -> None:
        """Reschedule refresh due to failure."""
        _LOGGER.debug("Update failed, scheduling a new one in 15 seconds")
        await asyncio.sleep(15)
        await self.async_refresh()

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        _LOGGER.debug(
            "Getting update for device %s (%s)", self.device.name, self.device.dsn
        )
        try:
            data = await self.device.get_all_data()
        except DopplerException as exc:
            _LOGGER.debug(
                "Exception received during update for device %s (%s): %s: %s",
                self.device.name,
                self.device.dsn,
                type(exc).__name__,
                exc,
            )
            if not self._entities_created:
                self.hass.async_create_task(self._reschedule_refresh())
            raise UpdateFailed() from exc
        else:
            _LOGGER.debug(
                "Finished getting update for device %s (%s)",
                self.device.name,
                self.device.dsn,
            )
        if not self.data:
            self._entities_created = True
            async_dispatcher_send(
                self.hass, f"{DOMAIN}_{self._entry.entry_id}_device_added", self.device
            )
        return data
