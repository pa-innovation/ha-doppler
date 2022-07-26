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
from .const import ATTR_TIME_MODE, ATTR_VOLUME_LEVEL, ATTR_AUDIO_PRESET, DOMAIN
from .entity import DopplerEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
) -> None:
    """Setup sensor platform."""
    coordinator: DopplerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices(
        [
            DopplerTimeModeNumber(coordinator, entry, device, "Time Mode"),
            DopplerSoundPresetSelect(coordinator, entry, device, "Audio Preset"),
            for device in coordinator.api.devices.values()
        ]
    )


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

    _attr_options = ["Preset 1", "Preset 2", "Preset 3", "Preset 4", "Preset 5"]

    @property
    def current_option(self) -> str:
        """Return the current option."""
        return str(self.coordinator.data[self.device.name][ATTR_SOUND_PRESET])

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self.coordinator.api.set_sound_preset(self.device, int(option))

        
