"""Doppler light platform."""
from __future__ import annotations

from doppyler.model.doppler import Doppler
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from . import DopplerDataUpdateCoordinator
from .const import DOMAIN


class DopplerEntity(CoordinatorEntity[DopplerDataUpdateCoordinator]):
    """Base class for a Doppler entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DopplerDataUpdateCoordinator,
        config_entry: ConfigEntry,
        device: Doppler,
        name: str,
    ):
        super().__init__(coordinator)
        self.config_entry = config_entry
        self.device = device

        self.device_data = coordinator.data[self.device.dsn]

        self._attr_name = name
        self._attr_unique_id = slugify(
            f"{self.config_entry.unique_id}_{self.device.dsn}_{self.name}"
        )
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, self.device.dsn)})
