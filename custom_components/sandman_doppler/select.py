"""Select platform for Doppler Sandman."""
from __future__ import annotations

from doppyler.const import (
    ATTR_TIME_MODE,
    ATTR_SOUND_PRESET,
    ATTR_WEATHER,
    ATTR_TIMEZONE,
)
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DopplerDataUpdateCoordinator
from .const import WEATHER_OPTIONS, DOMAIN
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
                DopplerTimeModeNumber(coordinator, entry, device, "Time Mode"),
                DopplerSoundPresetSelect(coordinator, entry, device, "Audio Preset"),
                DopplerWeatherModeSelect(coordinator, entry, device, "Weather Mode"),
                DopplerTimezoneSelect(coordinator, entry, device, "Timezone"),
            ]
        )
    async_add_devices(entities)


class DopplerTimeModeNumber(DopplerEntity, SelectEntity):
    """Doppler Time Mode Select class."""

    _attr_options = ["12", "24"]

    @property
    def current_option(self) -> str:
        """Return the current option."""
        return str(self.device_data[ATTR_TIME_MODE])

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self.device.set_time_mode(self.device, int(option))


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

    _attr_options = [
        "UTC",
        "US/Samoa",
        "US/Hawaii",
        "US/Aleutian",
        "Pacific/Marquesas",
        "Pacific/Gambier",
        "US/Alaska",
        "US/Pacific",
        "US/Arizona",
        "US/Mountain",
        "Canada/Saskatchewan",
        "US/Central",
        "America/Panama",
        "US/Eastern",
        "America/Puerto_Rico",
        "America/Caracas",
        "Canada/Newfoundland",
        "Canada/Atlantic",
        "Brazil",
        "Brazil/DeNoronha",
        "Atlantic/Cape_Verde",
        "Europe/London",
        "Europe/Prague",
        "Africa/Harare",
        "Asia/Jerusalem",
        "Asia/Baghdad",
        "Asia/Muscat",
        "Asia/Tehran",
        "Asia/Kabul",
        "Asia/Tashkent",
        "Asia/Kolkata",
        "Asia/Kathmandu",
        "Asia/Dhaka",
        "Asia/Rangoon",
        "Asia/Bangkok",
        "Australia/Perth",
        "Australia/Eucla",
        "Asia/Seoul",
        "Australia/Darwin",
        "Australia/Queensland",
        "Australia/Adelaide",
        "Asia/Magadan",
        "Australia/Sydney",
        "Pacific/Auckland",
        "Pacific/Tongatapu",
        "Pacific/Chatham",
    ]

    @property
    def current_option(self) -> str:
        """Return the current option."""
        return str(self.device_data[ATTR_TIMEZONE])

    async def async_select_option(self, option: str) -> str:
        """Change the selected option."""
        mode = await self.device.set_timezone(self.device, option)
        return str(mode)
