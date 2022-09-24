"""Sensor platform for Doppler Sandman."""
from __future__ import annotations

from dataclasses import dataclass
import logging

from doppyler.const import ATTR_CONNECTED_TO_ALEXA, ATTR_IS_IN_DAY_MODE
from doppyler.model.doppler import Doppler
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DopplerDataUpdateCoordinator
from .const import DOMAIN
from .entity import DopplerEntity

_LOGGER = logging.getLogger(__name__)


@dataclass
class DopplerBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Class to describe Doppler binary sensor entities."""

    state_key: str | None = None


BINARY_SENSOR_ENTITY_DESCRIPTIONS = [
    DopplerBinarySensorEntityDescription(
        "Day/Night Mode",
        name="Day/Night Mode",
        device_class="sandman_doppler__day_night",
        state_key=ATTR_IS_IN_DAY_MODE,
    ),
    DopplerBinarySensorEntityDescription(
        "Alexa",
        name="Alexa",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_key=ATTR_CONNECTED_TO_ALEXA,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
) -> None:
    """Setup binary sensor platform."""
    coordinator: DopplerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for device in coordinator.api.devices.values():
        entities.extend(
            [
                DopplerBinarySensor(coordinator, entry, device, description)
                for description in BINARY_SENSOR_ENTITY_DESCRIPTIONS
            ]
        )
    async_add_devices(entities)


class DopplerBinarySensor(DopplerEntity, BinarySensorEntity):
    """Doppler Day/Night Binary Sensor class."""

    def __init__(
        self,
        coordinator: DopplerDataUpdateCoordinator,
        entry: ConfigEntry,
        device: Doppler,
        description: DopplerBinarySensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, device, description.name)
        self.entity_description = description
        self._state_key = description.state_key

    @property
    def is_on(self) -> bool:
        """Return the state of the sensor."""
        return self.device_data[self._state_key]
