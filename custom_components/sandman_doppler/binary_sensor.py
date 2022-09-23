"""Sensor platform for Doppler Sandman."""
from __future__ import annotations

import logging

from doppyler.const import ATTR_IS_IN_DAY_MODE
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DopplerDataUpdateCoordinator
from .const import DOMAIN
from .entity import DopplerEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
) -> None:
    """Setup binary sensor platform."""
    coordinator: DopplerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for device in coordinator.api.devices.values():
        entities.extend(
            [DopplerDayNightSensor(coordinator, entry, device, "Day/Night Mode")]
        )
    async_add_devices(entities)


class DopplerDayNightSensor(DopplerEntity, BinarySensorEntity):
    """Doppler Day/Night Binary Sensor class."""

    _attr_device_class = "sandman_doppler__day_night"

    @property
    def is_on(self) -> bool:
        return self.device_data[ATTR_IS_IN_DAY_MODE]
