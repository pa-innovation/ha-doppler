"""Sensor platform for Doppler Sandman."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from doppyler.const import ATTR_ALARMS, ATTR_LIGHT_SENSOR_VALUE, ATTR_WIFI
from doppyler.model.doppler import Doppler
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import DopplerDataUpdateCoordinator
from .const import DOMAIN
from .entity import DopplerEntity

_LOGGER = logging.getLogger(__name__)


@dataclass
class DopplerSensorEntityDescription(SensorEntityDescription):
    """Class describing Doppler sensor entities."""

    state_key: str | None = None
    state_func: Callable[[Any], Any] | None = None


SENSOR_ENTITY_DESCRIPTIONS = [
    DopplerSensorEntityDescription(
        "Light Saturation",
        name="Light Saturation",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        state_key=ATTR_LIGHT_SENSOR_VALUE,
        state_func=lambda x: round(x, 2),
    ),
    DopplerSensorEntityDescription(
        "Wifi Connected Since",
        name="Wifi Connected Since",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.TIMESTAMP,
        state_key=ATTR_WIFI,
        state_func=lambda x: dt_util.now() - x.uptime,
    ),
    DopplerSensorEntityDescription(
        "Wifi SSID",
        name="Wifi SSID",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_key=ATTR_WIFI,
        state_func=lambda x: x.ssid,
    ),
    DopplerSensorEntityDescription(
        "Wifi Signal Strength",
        name="Wifi Signal Strength",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=PERCENTAGE,
        state_key=ATTR_WIFI,
        state_func=lambda x: int(x.signal_strength),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
) -> None:
    """Setup sensor platform."""
    coordinator: DopplerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for device in coordinator.api.devices.values():
        entities.extend(
            [
                DopplerSensor(coordinator, entry, device, description)
                for description in SENSOR_ENTITY_DESCRIPTIONS
            ]
        )
    async_add_devices(entities)


class DopplerSensor(DopplerEntity, SensorEntity):
    """Doppler sensor class."""

    def __init__(
        self,
        coordinator: DopplerDataUpdateCoordinator,
        entry: ConfigEntry,
        device: Doppler,
        description: DopplerSensorEntityDescription,
    ):
        """Initialize."""
        super().__init__(coordinator, entry, device, description.name)
        self.entity_description = description
        self._state_key: str = description.state_key
        self._state_func: Callable[[Any], Any] = description.state_func

    @property
    def native_value(self) -> Any:
        """Return the native value of the sensor."""
        return self._state_func(self.device_data[self._state_key])


# class DopplerAlarmsSensor(DopplerEntity,SensorEntity):
#     """Doppler Alarms Sensor class."""

#     _attr_state_class = SensorStateClass.MEASUREMENT

#     @property
#     def native_value(self) -> list[dict[str, Any]]:
#         """Return the native value of the sensor."""
#         mylist =[Alarm.to_dict(alarm) for alarm in self.device_data[ATTR_ALARMS]]
#         return mylist
