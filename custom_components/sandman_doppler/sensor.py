"""Sensor platform for Doppler Sandman."""
from __future__ import annotations

import logging
from typing import Any

from doppyler.model.alarm import Alarm
from doppyler.model.alarm import RepeatDayOfWeek
from doppyler.model.alarm import AlarmStatus
from doppyler.model.alarm import AlarmSource
from doppyler.model.alarm import AlarmDict
from doppyler.model.color import Color
from doppyler.model.color import ColorDict

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DopplerDataUpdateCoordinator
from .const import (
    ATTR_LIGHTSENSOR_VALUE,
    ATTR_DAYNIGHTMODE_VALUE,
    ATTR_ALARMS,
    ATTR_WIFI,
    DOMAIN,
)
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
                DopplerLightSensor(coordinator, entry, device, "Light Sensor Value"),
                DopplerDayNightSensor(coordinator, entry, device, "Day/Night Mode"),
                DopplerWifiUptimeSensor(coordinator, entry, device, "Wifi Uptime"),
                DopplerWifiSSIDSensor(coordinator, entry, device, "Wifi SSID"),
                DopplerWifiSignalStrengthSensor(coordinator, entry, device, "Wifi Signal Strength"),
#                DopplerAlarmsSensor(coordinator, entry, device, "Alarms"),
            ]
        )
    async_add_devices(entities)

class DopplerLightSensor(DopplerEntity,SensorEntity):
    
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
         return self.coordinator.data[self.device.name][ATTR_LIGHTSENSOR_VALUE]


class DopplerDayNightSensor(DopplerEntity,SensorEntity):
    
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
         return self.coordinator.data[self.device.name][ATTR_DAYNIGHTMODE_VALUE]


class DopplerWifiUptimeSensor(DopplerEntity,SensorEntity):
    
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
         return self.coordinator.data[self.device.name][ATTR_WIFI].uptime

     
class DopplerWifiSSIDSensor(DopplerEntity,SensorEntity):
    
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
         return self.coordinator.data[self.device.name][ATTR_WIFI].ssid

class DopplerWifiSignalStrengthSensor(DopplerEntity,SensorEntity):
    
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self.coordinator.data[self.device.name][ATTR_WIFI].signalstrength

# class DopplerAlarmsSensor(DopplerEntity,SensorEntity):
    
#     _attr_state_class = SensorStateClass.MEASUREMENT

#     @property
#     def native_value(self):
#         mylist =[Alarm.to_dict(alarm) for alarm in self.coordinator.data[self.device.name][ATTR_ALARMS]]
#         return mylist

