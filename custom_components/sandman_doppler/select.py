"""Select platform for Doppler Sandman."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import zoneinfo

from doppyler.const import (
    ATTR_SOUND_PRESET,
    ATTR_TIME_MODE,
    ATTR_TIMEZONE,
    ATTR_WEATHER,
)
from doppyler.model.doppler import Doppler
from doppyler.model.sound import SoundPreset
from doppyler.model.weather import WeatherMode
from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DopplerDataUpdateCoordinator
from .const import DOMAIN
from .entity import DopplerEntity
from .helpers import get_enum_from_name, normalize_enum_name


@dataclass
class DopplerEnumSelectEntityDescription(SelectEntityDescription):
    """Doppler Enum Select Entity Description."""

    enum_cls: Enum | None = None
    state_key: str | None = None
    set_value_func_name: str | None = None
    option_attr_name: str | None = None


ENTITY_DESCRIPTIONS = [
    DopplerEnumSelectEntityDescription(
        "Sound Preset",
        name="Sound Preset",
        enum_cls=SoundPreset,
        state_key=ATTR_SOUND_PRESET,
        set_value_func_name="set_sound_preset",
    ),
    DopplerEnumSelectEntityDescription(
        "Weather Mode",
        name="Weather Mode",
        enum_cls=WeatherMode,
        state_key=ATTR_WEATHER,
        option_attr_name="mode",
        set_value_func_name="set_weather_configuration",
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
                DopplerTimeModeSelect(coordinator, entry, device, "Time Mode"),
                DopplerTimezoneSelect(coordinator, entry, device, "Timezone"),
                *(
                    DopplerEnumSelect(coordinator, entry, device, description)
                    for description in ENTITY_DESCRIPTIONS
                ),
            ]
        )
    async_add_devices(entities)


class DopplerEnumSelect(DopplerEntity, SelectEntity):
    """Doppler Select class for enum attributes."""

    def __init__(
        self,
        coordinator: DopplerDataUpdateCoordinator,
        entry: ConfigEntry,
        device: Doppler,
        description: DopplerEnumSelectEntityDescription,
    ) -> None:
        """Initialize the select."""
        super().__init__(coordinator, entry, device, description.name)
        self.entity_description: DopplerEnumSelectEntityDescription = description
        self._enum_cls = description.enum_cls
        self._state_key = description.state_key
        self._set_value_func_name = description.set_value_func_name
        self._option_attr_name = description.option_attr_name

        self._attr_options = [
            normalize_enum_name(enum_val) for enum_val in self._enum_cls
        ]

    @property
    def current_option(self) -> str:
        """Return the current option."""
        current_option = self.device_data[self._state_key]
        if self._option_attr_name:
            return normalize_enum_name(getattr(current_option, self._option_attr_name))
        return normalize_enum_name(current_option)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        enum_val = get_enum_from_name(self._enum_cls, option)
        if self._option_attr_name:
            self.device_data[self._state_key] = await getattr(
                self.device, self._set_value_func_name
            )(**{self._option_attr_name: enum_val})
        else:
            self.device_data[self._state_key] = await getattr(
                self.device, self._set_value_func_name
            )(enum_val)


class DopplerTimeModeSelect(DopplerEntity, SelectEntity):
    """Doppler Time Mode Select class."""

    _attr_options = ["12", "24"]

    @property
    def current_option(self) -> str:
        """Return the current option."""
        return str(self.device_data[ATTR_TIME_MODE])

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        self.device_data[ATTR_TIME_MODE] = await self.device.set_time_mode(int(option))


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
        self.device_data[ATTR_TIMEZONE] = await self.device.set_timezone(option)
