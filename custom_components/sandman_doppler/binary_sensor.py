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
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
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

    @callback
    def async_add_device(device: Doppler) -> None:
        """Add Doppler binary sensor entities."""
        coordinator: DopplerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
        entities = [
            DopplerBinarySensor(coordinator, entry, device, description)
            for description in BINARY_SENSOR_ENTITY_DESCRIPTIONS
        ]
        async_add_devices(entities)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, f"{DOMAIN}_{entry.entry_id}_device_added", async_add_device
        )
    )


class DopplerBinarySensor(
    DopplerEntity[DopplerBinarySensorEntityDescription], BinarySensorEntity
):
    """Doppler Day/Night Binary Sensor class."""

    @property
    def is_on(self) -> bool:
        """Return the state of the sensor."""
        return self.device_data[self.ed.state_key]
