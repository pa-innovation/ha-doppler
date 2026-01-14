"""Sensor platform for Doppler Sandman."""

from __future__ import annotations

from collections.abc import Callable
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
    icon_lambda: Callable[[bool], str] | None = None


BINARY_SENSOR_ENTITY_DESCRIPTIONS = [
    DopplerBinarySensorEntityDescription(
        "Day/Night Mode",
        name="Day/Night Mode",
        device_class="sandman_doppler__day_night",
        state_key=ATTR_IS_IN_DAY_MODE,
        icon_lambda=lambda x: "mdi:weather-sunny" if x else "mdi:weather-night",
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
        coordinator: DopplerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
            device.dsn
        ]
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
    def is_on(self) -> bool | None:
        """Return the state of the sensor."""
        if self.ed.state_key is None:
            return None
        return self.device_data.get(self.ed.state_key)

    @property
    def icon(self) -> str | None:
        """Return the icon of the sensor."""
        if self.ed.icon_lambda and self.is_on is not None:
            return self.ed.icon_lambda(self.is_on)
        return super().icon
