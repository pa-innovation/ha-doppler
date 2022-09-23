"""Number platform for Doppler Sandman."""
from __future__ import annotations

import logging

from doppyler.const import ATTR_TIME_OFFSET, ATTR_VOLUME_LEVEL
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DopplerDataUpdateCoordinator
from .const import DOMAIN
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


class DopplerVolumeLevelNumber(DopplerEntity, NumberEntity):
    """Doppler Volume Level Number class."""

    _attr_native_step = 1
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_unit_of_measurement = PERCENTAGE

    @property
    def native_value(self) -> int:
        """Return the current value"""
        return self.device_data[ATTR_VOLUME_LEVEL]

    async def async_set_native_value(self, value: int) -> None:
        """Update the current volume value"""
        self.device_data[ATTR_VOLUME_LEVEL] = await self.device.set_volume_level(
            self.device, value
        )


class DopplerTimeOffsetNumber(DopplerEntity, NumberEntity):
    """Doppler Time Offset class."""

    _attr_native_step = 1
    _attr_native_min_value = -60
    _attr_native_max_value = 60
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_unit_of_measurement = "minutes"

    @property
    def native_value(self) -> int:
        """Return the current value"""
        return self.device_data[ATTR_TIME_OFFSET].total_seconds() // 60

    async def async_set_native_value(self, value: int) -> None:
        """Update the current volume value"""
        self.device_data[ATTR_TIME_OFFSET] = await self.device.set_offset(
            self.device, int(value)
        )
