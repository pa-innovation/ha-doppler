"""Doppler light platform."""
from __future__ import annotations

from doppyler.model.doppler import Doppler
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from . import DopplerDataUpdateCoordinator
from .const import DOMAIN


class DopplerEntity(CoordinatorEntity):
    """Base class for a Doppler entity."""

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
        self._name = name
        self._attr_name = f"{self.device.name}: {name}"

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return slugify(f"{self.config_entry.unique_id}_{self._name}")

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self.device.id),(DOMAIN, self.device.device_info.dsn)}}
