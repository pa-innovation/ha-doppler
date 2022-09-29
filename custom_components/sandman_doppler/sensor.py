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
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
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
    icon_func: Callable[[Any], Any] | None = None


SENSOR_ENTITY_DESCRIPTIONS = [
    DopplerSensorEntityDescription(
        "Light Detected",
        name="Light Detected",
        icon="mdi:lightbulb",
        state_class=SensorStateClass.MEASUREMENT,
        state_key=ATTR_LIGHT_SENSOR_VALUE,
        state_func=lambda x: round(x, 2),
    ),
    DopplerSensorEntityDescription(
        "Wifi: Connected Since",
        name="Wifi Connected Since",
        icon="mdi:connection",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.TIMESTAMP,
        state_key=ATTR_WIFI,
        state_func=lambda x: dt_util.now() - x.uptime,
    ),
    DopplerSensorEntityDescription(
        "Wifi: SSID",
        name="Wifi SSID",
        icon="mdi:wifi",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_key=ATTR_WIFI,
        state_func=lambda x: x.ssid,
    ),
    DopplerSensorEntityDescription(
        "Wifi: Signal Strength",
        name="Wifi Signal Strength",
        icon_func=lambda x: f"mdi:wifi-strength-{(x // 25) + 1 if x else 'outline'}",
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

    @callback
    def async_add_device(device: Doppler) -> None:
        """Add Doppler binary sensor entities."""
        coordinator: DopplerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][device.dsn]
        entities = [
            DopplerSensor(coordinator, entry, device, description)
            for description in SENSOR_ENTITY_DESCRIPTIONS
        ]
        async_add_devices(entities)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, f"{DOMAIN}_{entry.entry_id}_device_added", async_add_device
        )
    )


class DopplerSensor(DopplerEntity[DopplerSensorEntityDescription], SensorEntity):
    """Doppler sensor class."""

    @property
    def icon(self) -> str | None:
        """Return the icon for the entity."""
        if self.ed.icon_func:
            return self.ed.icon_func(self.native_value)
        return super().icon

    @property
    def native_value(self) -> Any:
        """Return the native value of the sensor."""
        return self.ed.state_func(self.device_data[self.ed.state_key])


# class DopplerAlarmsSensor(DopplerEntity,SensorEntity):
#     """Doppler Alarms Sensor class."""

#     _attr_state_class = SensorStateClass.MEASUREMENT

#     @property
#     def native_value(self) -> list[dict[str, Any]]:
#         """Return the native value of the sensor."""
#         mylist =[Alarm.to_dict(alarm) for alarm in self.device_data[ATTR_ALARMS]]
#         return mylist
