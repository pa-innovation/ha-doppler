"""The Sandman Doppler integration."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from doppyler.client import DopplerClient
from doppyler.exceptions import DopplerException
from doppyler.model.doppler import Doppler
from homeassistant.config_entries import ConfigEntry, ConfigEntryNotReady
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from custom_components.sandman_doppler.services import DopplerServices

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

    if not hass.data[DOMAIN][entry.entry_id].get("platform_setup_complete"):
        hass.data[DOMAIN][entry.entry_id]["platform_setup_complete"] = True
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

    DopplerServices(hass, ent_reg, dev_reg, client).async_register()

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
