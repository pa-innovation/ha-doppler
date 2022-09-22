"""Number platform for Doppler Sandman."""
from __future__ import annotations

import logging
from typing import Any

from doppyler.model.color import Color
from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DopplerDataUpdateCoordinator
from .const import ATTR_VOLUME_LEVEL, ATTR_TIMEOFFSET, DOMAIN
from .entity import DopplerEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
) -> None:
    """Setup sensor platform."""
    coordinator: DopplerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for device in coordinator.api.devices.values():
        entities.extend(
            [
                DopplerVolumeLevelNumber(coordinator, entry, device, "Volume Level"),
                DopplerTimeOffsetNumber(coordinator, entry, device, "Time Offset"),
            ]
        )
    async_add_devices(entities)


#    async_add_devices(
#        [
#            DopplerVolumeLevelNumber(coordinator, entry, device, "Volume Level"),
#            DopplerTimeOffsetNumber(coordinator, entry, device, "Time Offset"),
#            for device in coordinator.api.devices.values()
#        ]
#    )


class DopplerVolumeLevelNumber(DopplerEntity, NumberEntity):
    """Doppler Volume Level Number class."""

    _attr_native_step = 1
    _attr_native_min_value = 0
    _attr_native_max_value = 100

    # @property
    # def value(self) -> int:
    #     """Return the current value."""
    #     return self.coordinator.data[self.device.device_info.dsn][ATTR_VOLUME_LEVEL]

    @property
    def native_value(self) -> float | None:
        """Return the current value"""
        return self.coordinator.data[self.device.device_info.dsn][ATTR_VOLUME_LEVEL]

    async def async_set_native_value(self, value: float) -> None:
        """Update the current volume value"""
        self._attr_native_value = value
        await self.coordinator.api.set_volume_level(self.device, int(value))


class DopplerTimeOffsetNumber(DopplerEntity, NumberEntity):
    """Doppler Time Offset class."""

    _attr_native_step = 1
    _attr_native_min_value = -128
    _attr_native_max_value = +127
    _attr_mode = "box"

    @property
    def native_value(self) -> int:
        """Return the current value"""
        return self.coordinator.data[self.device.device_info.dsn][ATTR_TIMEOFFSET]

    async def async_set_native_value(self, value: int) -> None:
        """Update the current volume value"""
        self._attr_native_value = value
        await self.coordinator.api.set_offset(self.device, int(value))
