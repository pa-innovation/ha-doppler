"""Select platform for Doppler Sandman."""
from __future__ import annotations

import zoneinfo

from doppyler.const import (
    ATTR_SOUND_PRESET,
    ATTR_TIME_MODE,
    ATTR_TIMEZONE,
    ATTR_WEATHER,
)
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DopplerDataUpdateCoordinator
from .const import DOMAIN, WEATHER_OPTIONS
from .entity import DopplerEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
) -> None:
    """Setup sensor platform."""
    coordinator: DopplerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for device in coordinator.api.devices.values():
        entities.extend(
            [
                DopplerTimeModeSelect(coordinator, entry, device, "Time Mode"),
                DopplerSoundPresetSelect(coordinator, entry, device, "Audio Preset"),
                DopplerWeatherModeSelect(coordinator, entry, device, "Weather Mode"),
                DopplerTimezoneSelect(coordinator, entry, device, "Timezone"),
            ]
        )
    async_add_devices(entities)


class DopplerTimeModeSelect(DopplerEntity, SelectEntity):
    """Doppler Time Mode Select class."""

    _attr_options = ["12", "24"]

    @property
    def current_option(self) -> str:
        """Return the current option."""
        return str(self.device_data[ATTR_TIME_MODE])

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        self.device_data[ATTR_TIME_MODE] = await self.device.set_time_mode(
            self.device, int(option)
        )


class DopplerSoundPresetSelect(DopplerEntity, SelectEntity):
    """Doppler Time Mode Select class."""

    _attr_options = [
        "Preset 1 Balanced",
        "Preset 2 Bass Boost",
        "Preset 3 Treble Boost",
        "Preset 4 Mids Boost",
        "Preset 5 Untuned",
    ]

    @property
    def current_option(self) -> str:
        """Return the current option."""
        return str(self.device_data[ATTR_SOUND_PRESET])

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option == "Preset 1 Balanced":
            await self.device.set_sound_preset(self.device, "PRESET1")
        elif option == "Preset 2 Bass Boost":
            await self.device.set_sound_preset(self.device, "PRESET2")
        elif option == "Preset 3 Treble Boost":
            await self.device.set_sound_preset(self.device, "PRESET3")
        elif option == "Preset 4 Mids Boost":
            await self.device.set_sound_preset(self.device, "PRESET4")
        elif option == "Preset 5 Untuned":
            await self.device.set_sound_preset(self.device, "PRESET5")


class DopplerWeatherModeSelect(DopplerEntity, SelectEntity):
    """Doppler Time Mode Select class."""

    _attr_options = WEATHER_OPTIONS

    @property
    def current_option(self) -> str:
        """Return the current option."""
        return str(self.device_data[ATTR_WEATHER].mode.name)

    async def async_select_option(self, option: str) -> str:
        """Change the selected option."""
        mode = await self.device.set_weather_configuration(
            self.device, mode=self._attr_options.index(option)
        )
        return self._attr_options[mode]


class DopplerTimezoneSelect(DopplerEntity, SelectEntity):
    """Doppler Timezone Select class."""

    @property
    def options(self) -> list[str]:
        """Return a list of available options."""
        return sorted(list(zoneinfo.available_timezones()))

    @property
    def current_option(self) -> str:
        """Return the current option."""
        return str(self.device_data[ATTR_TIMEZONE])

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        self.device_data[ATTR_TIMEZONE] = await self.device.set_timezone(self.device, option)
