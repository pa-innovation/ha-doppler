"""The Sandman Doppler integration."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from aiohttp.client import DEFAULT_TIMEOUT, ClientTimeout
from doppyler.client import DopplerClient
from doppyler.exceptions import DopplerException
from doppyler.model.alarm import Alarm, AlarmDict, AlarmSource, AlarmStatus
from doppyler.model.color import Color
from doppyler.model.doppler import Doppler
from doppyler.model.light_bar import LightbarDisplayDict, LightbarDisplayEffect
from doppyler.model.main_display_text import MainDisplayText, MainDisplayTextDict
from doppyler.model.mini_display_number import MiniDisplayNumber, MiniDisplayNumberDict
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_AREA_ID,
    ATTR_DEVICE_ID,
    ATTR_ENTITY_ID,
    CONF_EMAIL,
    CONF_PASSWORD,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.service import ServiceCall
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, PLATFORMS

SCAN_INTERVAL = timedelta(seconds=900)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up config entry."""
    hass.data.setdefault(DOMAIN, {})

    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]

    session = async_create_clientsession(hass, timeout=ClientTimeout(DEFAULT_TIMEOUT))
    client = DopplerClient(email, password, client_session=session, local_control=True)

    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    hass.data[DOMAIN][entry.entry_id] = coordinator = DopplerDataUpdateCoordinator(
        hass, entry, client, dev_reg
    )
    await coordinator.async_config_entry_first_refresh()

    @callback
    def async_on_device_added(device: Doppler) -> None:
        """Handle device added."""
        _LOGGER.debug("Device added: %s", device)
        async_dispatcher_send(hass, f"{DOMAIN}_{entry.entry_id}_device_added", device)

    @callback
    def async_on_device_removed(device: Doppler) -> None:
        """Handle device removed."""
        _LOGGER.debug("Device removed: %s", device)
        dev_entry = dev_reg.async_get_device({(DOMAIN, device.dsn)})
        assert dev_entry
        dev_reg.async_remove_device(dev_entry.id)

    entry.async_on_unload(client.on_device_added(async_on_device_added))
    entry.async_on_unload(client.on_device_removed(async_on_device_removed))

    # Load initial devices after the first refresh
    for device in client.devices.values():
        async_on_device_added(device)

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

    async def handle_set_alarm_service(call: ServiceCall) -> None:
        if "repeat" in call.data:
            r = call.data["repeat"]
        else:
            r = ""
        alarmdict = AlarmDict(
            id=int(call.data["alarm_id"]),
            name=call.data["alarm_name"],
            time_hr=int(call.data["alarm_time"].split(":")[0]),
            time_min=int(call.data["alarm_time"].split(":")[1]),
            repeat=r,
            color=Color(
                red=int(call.data["color"][0]),
                green=int(call.data["color"][1]),
                blue=int(call.data["color"][2]),
            ),
            volume=int(call.data["volume"]),
            status=AlarmStatus.SET,
            src=AlarmSource.APP,
            sound=call.data["sound"],
        )
        for device in get_dopplers_from_svc_targets(call):
            result = await device.add_alarm(Alarm.from_dict(alarmdict))
            _LOGGER.warning(f"alarm result was {result}")

    async def handle_delete_alarm_service(call: ServiceCall) -> None:
        for device in get_dopplers_from_svc_targets(call):
            await device.delete_alarm(int(call.data["alarm_id"]))

    async def handle_set_main_display_service(call: ServiceCall) -> None:

        _LOGGER.warning(f"Called handle_set_main_display service")
        mdt_dict = MainDisplayTextDict(
            {
                "text": str(call.data["display_text"]),
                "duration": int(call.data["display_duration"]),
                "speed": int(call.data["display_speed"]),
                "color": [
                    int(call.data["display_color"][0]),
                    int(call.data["display_color"][1]),
                    int(call.data["display_color"][2]),
                ],
            }
        )

        for device in get_dopplers_from_svc_targets(call):
            await device.set_main_display_text(MainDisplayText.from_dict(mdt_dict))

    async def handle_set_mini_display_service(call: ServiceCall) -> None:
        _LOGGER.warning(f"Called handle_display_num_mini service")
        mdn_dict = MiniDisplayNumberDict(
            {
                "num": int(call.data["display_number"]),
                "duration": int(call.data["display_duration"]),
                "color": [
                    int(call.data["display_color"][0]),
                    int(call.data["display_color"][1]),
                    int(call.data["display_color"][2]),
                ],
            }
        )

        for device in get_dopplers_from_svc_targets(call):
            await device.set_mini_display_number(MiniDisplayNumber.from_dict(mdn_dict))

    async def handle_set_lightbar_color_service(call: ServiceCall) -> None:
        _LOGGER.warning(f"data was {call.data}")
        _LOGGER.warning(f"Called handle_set_lightbar_color service")
        color_list = []
        for c in [
            call.data.get("lightbar_color1"),
            call.data.get("lightbar_color2"),
            call.data.get("lightbar_color3"),
            call.data.get("lightbar_color4"),
            call.data.get("lightbar_color5"),
            call.data.get("lightbar_color6"),
            call.data.get("lightbar_color7"),
            call.data.get("lightbar_color8"),
            call.data.get("lightbar_color9"),
            call.data.get("lightbar_color10"),
            call.data.get("lightbar_color11"),
            call.data.get("lightbar_color12"),
        ]:
            if c is not None:
                color_list.append([c[0], c[1], c[2]])
        s = call.data.get("lightbar_sparkle")
        r = call.data.get("lightbar_rainbow")

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
                "duration": int(call.data["lightbar_duration"]),
                "speed": int(call.data["lightbar_speed"]),
                "attributes": attributes_dict,
            }
        )
        _LOGGER.warning(f"lbde_dict={lbde_dict}")
        for device in get_dopplers_from_svc_targets(call):
            retval = await device.set_light_bar_effect(
                LightbarDisplayEffect.from_dict(lbde_dict)
            )
        _LOGGER.warning(f"retval={retval.to_dict()}")

    async def handle_set_each_lightbar_color_service(call: ServiceCall) -> None:
        _LOGGER.warning(f"data was {call.data}")
        _LOGGER.warning(f"Called handle_set_lightbar_color service")
        color_list = []
        for c in [
            call.data.get("lightbar_color1"),
            call.data.get("lightbar_color2"),
            call.data.get("lightbar_color3"),
            call.data.get("lightbar_color4"),
            call.data.get("lightbar_color5"),
            call.data.get("lightbar_color6"),
            call.data.get("lightbar_color7"),
            call.data.get("lightbar_color8"),
            call.data.get("lightbar_color9"),
            call.data.get("lightbar_color10"),
            call.data.get("lightbar_color11"),
            call.data.get("lightbar_color12"),
            call.data.get("lightbar_color13"),
            call.data.get("lightbar_color14"),
            call.data.get("lightbar_color15"),
            call.data.get("lightbar_color16"),
            call.data.get("lightbar_color17"),
            call.data.get("lightbar_color18"),
            call.data.get("lightbar_color19"),
            call.data.get("lightbar_color20"),
            call.data.get("lightbar_color21"),
            call.data.get("lightbar_color22"),
            call.data.get("lightbar_color23"),
            call.data.get("lightbar_color24"),
            call.data.get("lightbar_color25"),
            call.data.get("lightbar_color26"),
            call.data.get("lightbar_color27"),
            call.data.get("lightbar_color28"),
            call.data.get("lightbar_color29"),
        ]:
            if c is not None:
                color_list.append([c[0], c[1], c[2]])
        s = call.data.get("lightbar_sparkle")
        r = call.data.get("lightbar_rainbow")

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
                "duration": int(call.data["lightbar_duration"]),
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

    async def handle_set_lightbar_blink_service(call: ServiceCall) -> None:
        _LOGGER.warning(f"data was {call.data}")
        _LOGGER.warning(f"Called handle_set_lightbar_color service")
        color_list = []
        for c in [
            call.data.get("lightbar_color1"),
            call.data.get("lightbar_color2"),
            call.data.get("lightbar_color3"),
            call.data.get("lightbar_color4"),
            call.data.get("lightbar_color5"),
            call.data.get("lightbar_color6"),
            call.data.get("lightbar_color7"),
            call.data.get("lightbar_color8"),
            call.data.get("lightbar_color9"),
            call.data.get("lightbar_color10"),
            call.data.get("lightbar_color11"),
            call.data.get("lightbar_color12"),
        ]:
            if c is not None:
                color_list.append([c[0], c[1], c[2]])
        s = call.data.get("lightbar_sparkle")
        r = call.data.get("lightbar_rainbow")
        sp = call.data.get("lightbar_speed")

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
                "duration": int(call.data["lightbar_duration"]),
                "speed": int(call.data["lightbar_speed"]),
                "attributes": attributes_dict,
            }
        )

        _LOGGER.warning(f"lbde_dict={lbde_dict}")
        for device in get_dopplers_from_svc_targets(call):
            retval = await device.set_light_bar_effect(
                LightbarDisplayEffect.from_dict(lbde_dict)
            )
        _LOGGER.warning(f"retval={retval.to_dict()}")

    async def handle_set_lightbar_pulse_service(call: ServiceCall) -> None:
        _LOGGER.warning(f"data was {call.data}")
        _LOGGER.warning(f"Called handle_set_lightbar_pulse service")
        color_list = []
        for c in [
            call.data.get("lightbar_color1"),
            call.data.get("lightbar_color2"),
            call.data.get("lightbar_color3"),
            call.data.get("lightbar_color4"),
            call.data.get("lightbar_color5"),
            call.data.get("lightbar_color6"),
            call.data.get("lightbar_color7"),
            call.data.get("lightbar_color8"),
            call.data.get("lightbar_color9"),
            call.data.get("lightbar_color10"),
            call.data.get("lightbar_color11"),
            call.data.get("lightbar_color12"),
        ]:
            if c is not None:
                color_list.append([c[0], c[1], c[2]])
        s = call.data.get("lightbar_sparkle")
        r = call.data.get("lightbar_rainbow")
        sp = call.data.get("lightbar_speed")
        gp = call.data.get("lightbar_gap")

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
                "duration": int(call.data["lightbar_duration"]),
                "speed": int(call.data["lightbar_speed"]),
                "attributes": attributes_dict,
            }
        )

        _LOGGER.warning(f"lbde_dict={lbde_dict}")
        for device in get_dopplers_from_svc_targets(call):
            retval = await device.set_light_bar_effect(
                LightbarDisplayEffect.from_dict(lbde_dict)
            )
        _LOGGER.warning(f"retval={retval.to_dict()}")

    async def handle_set_lightbar_comet_service(call: ServiceCall) -> None:
        _LOGGER.warning(f"data was {call.data}")
        _LOGGER.warning(f"Called handle_set_lightbar_pulse service")
        color_list = []
        for c in [
            call.data.get("lightbar_color1"),
            call.data.get("lightbar_color2"),
            call.data.get("lightbar_color3"),
            call.data.get("lightbar_color4"),
            call.data.get("lightbar_color5"),
            call.data.get("lightbar_color6"),
            call.data.get("lightbar_color7"),
            call.data.get("lightbar_color8"),
            call.data.get("lightbar_color9"),
            call.data.get("lightbar_color10"),
            call.data.get("lightbar_color11"),
            call.data.get("lightbar_color12"),
        ]:
            if c is not None:
                color_list.append([c[0], c[1], c[2]])
        s = call.data.get("lightbar_sparkle")
        r = call.data.get("lightbar_rainbow")
        sz = call.data.get("lightbar_size")
        direct = call.data.get("lightbar_direction")

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
                "duration": int(call.data["lightbar_duration"]),
                "speed": int(call.data["lightbar_speed"]),
                "attributes": attributes_dict,
            }
        )

        _LOGGER.warning(f"lbde_dict={lbde_dict}")
        for device in get_dopplers_from_svc_targets(call):
            retval = await device.set_light_bar_effect(
                LightbarDisplayEffect.from_dict(lbde_dict)
            )
        _LOGGER.warning(f"retval={retval.to_dict()}")

    async def handle_set_lightbar_sweep_service(call: ServiceCall) -> None:
        _LOGGER.warning(f"data was {call.data}")
        _LOGGER.warning(f"Called handle_set_lightbar_sweep service")
        color_list = []
        for c in [
            call.data.get("lightbar_color1"),
            call.data.get("lightbar_color2"),
            call.data.get("lightbar_color3"),
            call.data.get("lightbar_color4"),
            call.data.get("lightbar_color5"),
            call.data.get("lightbar_color6"),
            call.data.get("lightbar_color7"),
            call.data.get("lightbar_color8"),
            call.data.get("lightbar_color9"),
            call.data.get("lightbar_color10"),
            call.data.get("lightbar_color11"),
            call.data.get("lightbar_color12"),
        ]:
            if c is not None:
                color_list.append([c[0], c[1], c[2]])
        s = call.data.get("lightbar_sparkle")
        r = call.data.get("lightbar_rainbow")
        sp = call.data.get("lightbar_speed")
        gp = call.data.get("lightbar_gap")
        sz = call.data.get("lightbar_size")
        direct = call.data.get("lightbar_direction")

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
                "duration": int(call.data["lightbar_duration"]),
                "speed": int(call.data["lightbar_speed"]),
                "attributes": attributes_dict,
            }
        )

        _LOGGER.warning(f"lbde_dict={lbde_dict}")
        for device in get_dopplers_from_svc_targets(call):
            retval = await device.set_light_bar_effect(
                LightbarDisplayEffect.from_dict(lbde_dict)
            )
        _LOGGER.warning(f"retval={retval.to_dict()}")

    hass.services.async_register(DOMAIN, "setalarm", handle_set_alarm_service)
    hass.services.async_register(
        DOMAIN, "deletealarm", handle_delete_alarm_service
    )
    hass.services.async_register(
        DOMAIN, "displaytextmain", handle_set_main_display_service
    )
    hass.services.async_register(
        DOMAIN, "displaynummini", handle_set_mini_display_service
    )
    hass.services.async_register(
        DOMAIN, "setlightbarcolor", handle_set_lightbar_color_service
    )
    hass.services.async_register(
        DOMAIN, "seteachlightbarcolor", handle_set_each_lightbar_color_service
    )
    hass.services.async_register(
        DOMAIN, "setlightbarblink", handle_set_lightbar_blink_service
    )
    hass.services.async_register(
        DOMAIN, "setlightbarpulse", handle_set_lightbar_pulse_service
    )
    hass.services.async_register(
        DOMAIN, "setlightbarcomet", handle_set_lightbar_comet_service
    )
    hass.services.async_register(
        DOMAIN, "setlightbarsweep", handle_set_lightbar_sweep_service
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
        dev_reg: dr.DeviceRegistry,
    ) -> None:
        """Initialize."""
        self.data: dict[str, dict[str, Any]] = {}
        self.api = client
        self.platforms = []
        self._dev_reg = dev_reg
        self._entry = entry

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        data: dict[dict[str, Any]] = {}
        await self.api.get_devices()

        try:
            for device in self.api.devices.values():
                _LOGGER.debug(
                    "Getting update for device %s (%s)", device.name, device.dsn
                )
                self._dev_reg.async_get_or_create(
                    config_entry_id=self._entry.entry_id,
                    identifiers={(DOMAIN, device.dsn)},
                    manufacturer=device.device_info.manufacturer,
                    model=device.device_info.model_number,
                    sw_version=device.device_info.software_version,
                    hw_version=device.device_info.firmware_version,
                    name=device.name,
                )
                data[device.dsn] = await device.get_all_data()
                _LOGGER.debug(
                    "Finished getting update for device %s (%s)",
                    device.name,
                    device.dsn,
                )
        except DopplerException as exc:
            _LOGGER.debug(
                "Exception received during update for device %s (%s): %s: %s",
                device.name,
                device.dsn,
                type(exc).__name__,
                exc,
            )
            raise UpdateFailed() from exc
        return data
