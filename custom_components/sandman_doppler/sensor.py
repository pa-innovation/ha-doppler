"""Sensor platform for Doppler Sandman."""
from __future__ import annotations

from datetime import datetime
import logging

from doppyler.const import ATTR_ALARMS, ATTR_LIGHT_SENSOR_VALUE, ATTR_WIFI
from homeassistant.components.sensor import SensorEntity, SensorStateClass
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


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
) -> None:
    """Setup sensor platform."""
    coordinator: DopplerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for device in coordinator.api.devices.values():
        entities.extend(
            [
                DopplerLightSaturationSensor(
                    coordinator, entry, device, "Light Saturation"
                ),
                DopplerWifiConnectedSinceSensor(
                    coordinator, entry, device, "Wifi Connected Since"
                ),
                DopplerWifiSSIDSensor(coordinator, entry, device, "Wifi SSID"),
                DopplerWifiSignalStrengthSensor(
                    coordinator, entry, device, "Wifi Signal Strength"
                ),
                #                DopplerAlarmsSensor(coordinator, entry, device, "Alarms"),
            ]
        )
    async_add_devices(entities)


class DopplerLightSaturationSensor(DopplerEntity, SensorEntity):
    """Doppler Light Saturation Sensor class."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE

    @property
    def native_value(self) -> float:
        """Return the native value of the sensor."""
        return round(self.device_data[ATTR_LIGHT_SENSOR_VALUE], 1)


class DopplerWifiConnectedSinceSensor(DopplerEntity, SensorEntity):
    """Doppler Wifi Connected Since Sensor class."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> datetime:
        """Return the native value of the sensor."""
        return dt_util.now() - self.device_data[ATTR_WIFI].uptime


class DopplerWifiSSIDSensor(DopplerEntity, SensorEntity):
    """Doppler Wifi SSID Sensor class."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        return self.device_data[ATTR_WIFI].ssid


class DopplerWifiSignalStrengthSensor(DopplerEntity, SensorEntity):
    """Doppler Wifi Signal Strength Sensor class."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = PERCENTAGE

    @property
    def native_value(self) -> int:
        """Return the native value of the sensor."""
        return int(self.device_data[ATTR_WIFI].signal_strength)


# class DopplerAlarmsSensor(DopplerEntity,SensorEntity):
#     """Doppler Alarms Sensor class."""

#     _attr_state_class = SensorStateClass.MEASUREMENT

#     @property
#     def native_value(self) -> list[dict[str, Any]]:
#         """Return the native value of the sensor."""
#         mylist =[Alarm.to_dict(alarm) for alarm in self.device_data[ATTR_ALARMS]]
#         return mylist
