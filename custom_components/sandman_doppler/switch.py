"""Switch platform for Doppler Sandman."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DopplerDataUpdateCoordinator
from .const import ATTR_COLON_BLINK, DOMAIN
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
#        return self._device["current_state"] > 0

#    @property
#    def native_value(self) -> float |None:
#        """Return the current value"""
#        return self.coordinator.data[self.device.name][ATTR_VOLUME_LEVEL]
    
#    async def async_set_native_value(self, value:float) -> None:
#        """Update the current volume value"""
#        self._attr_native_value = value
#        await self.coordinator.api.set_volume_level(self.device,int(value))


