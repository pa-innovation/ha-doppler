"""Select platform for Doppler Sandman."""
from __future__ import annotations

import logging
from typing import Any

from doppyler.model.color import Color
from doppyler.model.dotw import DOTWStatus
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DopplerDataUpdateCoordinator
from .const import ATTR_TIME_MODE, ATTR_VOLUME_LEVEL, ATTR_SOUND_PRESET, ATTR_WEATHER_MODE, DOMAIN
from .entity import DopplerEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
) -> None:
    """Setup sensor platform."""
    coordinator: DopplerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities= []
    for device in coordinator.api.devices.values():
        entities.extend(
            [
                DopplerTimeModeNumber(coordinator, entry, device, "Time Mode"),
                DopplerSoundPresetSelect(coordinator, entry, device, "Audio Preset"),
                DopplerWeatherModeSelect(coordinator, entry, device, "Weather Mode"),
            ]
        )
    async_add_devices(entities)

    


class DopplerTimeModeNumber(DopplerEntity, SelectEntity):
    """Doppler Time Mode Select class."""

    _attr_options = ["12", "24"]

    @property
    def current_option(self) -> str:
        """Return the current option."""
        return str(self.coordinator.data[self.device.name][ATTR_TIME_MODE])

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self.coordinator.api.set_time_mode(self.device, int(option))

class DopplerSoundPresetSelect(DopplerEntity, SelectEntity):
    """Doppler Time Mode Select class."""

    _attr_options = [
        "Preset 1 Balanced",
        "Preset 2 Bass Boost",
        "Preset 3 Treble Boost",
        "Preset 4 Mids Boost",
        "Preset 5 Untuned"
    ]

    @property
    def current_option(self) -> str:
        """Return the current option."""
        return str(self.coordinator.data[self.device.name][ATTR_SOUND_PRESET])

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option=="Preset 1 Balanced":
            await self.coordinator.api.set_sound_preset(self.device, "PRESET1")
        elif option=="Preset 2 Bass Boost":
            await self.coordinator.api.set_sound_preset(self.device, "PRESET2")
        elif option=="Preset 3 Treble Boost":
            await self.coordinator.api.set_sound_preset(self.device, "PRESET3")
        elif option=="Preset 4 Mids Boost":
            await self.coordinator.api.set_sound_preset(self.device, "PRESET4")        
        elif option=="Preset 5 Untuned":
            await self.coordinator.api.set_sound_preset(self.device, "PRESET5")

class DopplerWeatherModeSelect(DopplerEntity, SelectEntity):
    """Doppler Time Mode Select class."""

    _attr_options = ["Off" ,               #0
                     "Daily Max F",        #1
                     "Daily Max C",        #2
                     "Daily Avg Humidity", #3
                     "Daily AQI",          #4
                     "Daily Min F",        #5
                     "Daily Min C",        #6
                     "Daily Humidity Min", #7
                     "Daily Humididy Max", #8
                     "Hourly F",           #9
                     "Hourly C",           #10
                     "Hourly Humidity",    #11
                     "Hourly AQI",         #12
                     ]

    @property
    def current_option(self) -> str:
        """Return the current option."""
        return str(self.coordinator.data[self.device.name][ATTR_WEATHER_MODE])

    async def async_select_option(self, option: str) -> str:
        """Change the selected option."""
        mode = await self.coordinator.api.set_weather_mode(self.device, self._attr_options.index(option))
        return self._attr_options[mode]

            
