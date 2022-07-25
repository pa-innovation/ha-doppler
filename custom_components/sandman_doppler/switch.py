"""Switch platform for Doppler Sandman."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DopplerDataUpdateCoordinator
from .const import ATTR_COLON_BLINK, ATTR_USE_COLON, DOMAIN
from .entity import DopplerEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
) -> None:
    """Setup sensor platform."""
    coordinator: DopplerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices(
        [
            ColonBlinkSwitch(coordinator, entry, device, "Blink Colon")
            UseColonSwitch(coordinator, entry, device, "Use Colon")
            for device in coordinator.api.devices.values()
        ]
    )


class ColonBlinkSwitch(DopplerEntity, SwitchEntity):
    """Doppler ColonBlink class."""
    _attr_device_class="switch"

    async def async_turn_on(self, **kwargs):
        """Turn Colon Blinking On"""
        await self.coordinator.api.set_colon_blink_mode(
            self.device, True)


    async def async_turn_off(self, **kwargs):
        """Turn Colon Blink Off"""
        await self.coordinator.api.set_colon_blink_mode(
            self.device, False)
        

    @property
    def is_on(self):
        """Return true if device is on."""
        return self.coordinator.data[self.device.name][ATTR_COLON_BLINK]


class UseColonSwitch(DopplerEntity, SwitchEntity):
    """Doppler UseColon class."""
    _attr_device_class="switch"

    async def async_turn_on(self, **kwargs):
        """Turn Colon Blinking On"""
        await self.coordinator.api.set_use_colon_mode(
            self.device, True)


    async def async_turn_off(self, **kwargs):
        """Turn Colon Blink Off"""
        await self.coordinator.api.set_use_colon_mode(
            self.device, False)
        

    @property
    def is_on(self):
        """Return true if device is on."""
        return self.coordinator.data[self.device.name][ATTR_USE_COLON]
