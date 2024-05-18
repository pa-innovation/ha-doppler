"""The Sandman Doppler integration."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import functools
import logging
from typing import Any

from doppyler.client import DopplerClient
from doppyler.exceptions import DopplerException
from doppyler.model.doppler import Doppler

from homeassistant.config_entries import ConfigEntry, ConfigEntryNotReady
from homeassistant.const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    EVENT_HOMEASSISTANT_STARTED,
    Platform,
)
from homeassistant.core import CoreState, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.network import get_url
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .http import DopplerWebhookView
from .services import DopplerServices

SCAN_INTERVAL = timedelta(seconds=60)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SIREN,
    Platform.SWITCH,
]


async def _get_devices(client: DopplerClient) -> None:
    """Helper function to get devices from cloud."""
    try:
        await client.get_devices()
    except DopplerException as err:
        _LOGGER.warning("Error getting devices: %s", err)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Sandman Doppler component."""
    hass.http.register_view(DopplerWebhookView())
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up config entry."""
    hass.data.setdefault(DOMAIN, {}).setdefault(entry.entry_id, {})

    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]

    session = async_get_clientsession(hass)
    client = DopplerClient(
        email, password, client_session=session, local_api_semaphore_limit=1
    )

    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)

    if not hass.data[DOMAIN][entry.entry_id].get("platform_setup_complete"):
        hass.data[DOMAIN][entry.entry_id]["platform_setup_complete"] = True
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    @callback
    def async_on_device_added(doppler: Doppler) -> None:
        """Handle device added."""
        # Create a new coordinator and device registry entry for every new device and
        # trigger an initial refresh to get information
        _LOGGER.debug("Doppler added: %s", doppler)
        dev_entry = dev_reg.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, doppler.dsn)},
            manufacturer=doppler.device_info.manufacturer,
            model=doppler.device_info.model_number,
            sw_version=doppler.device_info.software_version,
            hw_version=doppler.device_info.firmware_version,
            name=doppler.name,
        )
        hass.data[DOMAIN][entry.entry_id][
            doppler.dsn
        ] = coordinator = DopplerDataUpdateCoordinator(
            hass, entry, client, doppler, dev_entry
        )
        hass.async_create_task(coordinator.async_refresh())

    @callback
    def async_on_device_removed(doppler: Doppler) -> None:
        """Handle device removed."""
        _LOGGER.debug("Doppler removed: %s", doppler)
        dev_entry = dev_reg.async_get_device({(DOMAIN, doppler.dsn)})
        assert dev_entry
        dev_reg.async_remove_device(dev_entry.id)
        hass.data[DOMAIN][entry.entry_id].pop(doppler.dsn)

    entry.async_on_unload(client.on_device_added(async_on_device_added))
    entry.async_on_unload(client.on_device_removed(async_on_device_removed))

    try:
        await client.get_token()
    except DopplerException as err:
        raise ConfigEntryNotReady from err

    # Every five minutes we will query for new devices - this will activate our add
    # and remove device listeners if the list changes
    entry.async_on_unload(
        async_track_time_interval(
            hass, functools.partial(_get_devices, client), timedelta(minutes=5)
        )
    )

    # Since getting devies can take some time, we delay querying until after startup
    # so we don't hold everything up.
    if hass.state == CoreState.running:
        hass.async_create_task(_get_devices(client))
    else:
        hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STARTED,
            lambda _: hass.async_create_task(_get_devices(client)),
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
        doppler: Doppler,
        device_entry: dr.DeviceEntry,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass, _LOGGER, name=f"{DOMAIN}_{doppler.dsn}", update_interval=SCAN_INTERVAL
        )
        self.data: dict[str, Any] = {}
        self.api = client
        self.doppler = doppler
        self._entry = entry
        self._entities_created = False
        base_url = get_url(
            self.hass,
            require_ssl=False,
            require_standard_port=False,
            allow_internal=True,
            allow_external=True,
            allow_cloud=True,
            allow_ip=True,
            prefer_external=False,
            prefer_cloud=False,
        )
        self._webhook_url = (
            f"{base_url}/api/sandman_doppler/smart_button/{device_entry.id}"
        )

    async def _reschedule_refresh(self) -> None:
        """Reschedule refresh due to failure."""
        _LOGGER.debug("Update failed, scheduling a new one in 15 seconds")
        await asyncio.sleep(15)
        await self.async_refresh()

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        _LOGGER.debug(
            "Getting update for device %s (%s)", self.doppler.name, self.doppler.dsn
        )
        try:
            data = await self.doppler.get_all_data()
        except DopplerException as exc:
            _LOGGER.debug(
                "Exception received during update for device %s (%s): %s: %s",
                self.doppler.name,
                self.doppler.dsn,
                type(exc).__name__,
                exc,
            )
            if not self._entities_created:
                self.hass.async_create_task(self._reschedule_refresh())
            raise UpdateFailed() from exc
        else:
            _LOGGER.debug(
                "Finished getting update for device %s (%s)",
                self.doppler.name,
                self.doppler.dsn,
            )
        if not self.data:
            self._entities_created = True
            await asyncio.gather(
                *[
                    self.doppler.set_smart_button_configuration(
                        button_num, url=self._webhook_url, command="HA"
                    )
                    for button_num in range(1, 3)
                ]
            )
            async_dispatcher_send(
                self.hass, f"{DOMAIN}_{self._entry.entry_id}_device_added", self.doppler
            )
        return data
