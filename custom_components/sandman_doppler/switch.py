"""Switch platform for Doppler Sandman."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DopplerDataUpdateCoordinator
from .const import ATTR_VOLUME_LEVEL, DOMAIN
from .entity import DopplerEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
) -> None:
    """Setup sensor platform."""
    coordinator: DopplerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices(
        [
            ColonBlinkSwitch(coordinator, entry, device, "Volume Level")
            for device in coordinator.api.devices.values()
        ]
    )


class ColonBlinkSwitch(DopplerEntity, SwitchEntity):
    """Doppler ColonBlink class."""
    _attr_device_class="switch"
    async def turn_on(self, **kwargs):
        """Turn Colon Blinking On"""

    async def turn_off(self, **kwargs):
        """Turn Colon Blink Off"""

#    @property
#    def native_value(self) -> float |None:
#        """Return the current value"""
#        return self.coordinator.data[self.device.name][ATTR_VOLUME_LEVEL]
    
#    async def async_set_native_value(self, value:float) -> None:
#        """Update the current volume value"""
#        self._attr_native_value = value
#        await self.coordinator.api.set_volume_level(self.device,int(value))


