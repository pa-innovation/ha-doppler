"""Switch platform for Doppler Sandman."""
from __future__ import annotations

from dataclasses import dataclass
import logging

from doppyler.const import (
    ATTR_ALEXA_TAP_TO_TALK_TONE_ENABLED,
    ATTR_ALEXA_USE_ASCENDING_ALARMS,
    ATTR_ALEXA_WAKE_WORD_TONE_ENABLED,
    ATTR_COLON_BLINK,
    ATTR_DISPLAY_SECONDS,
    ATTR_SOUND_PRESET_MODE,
    ATTR_USE_COLON,
    ATTR_USE_LEADING_ZERO,
    ATTR_WEATHER,
)
from doppyler.model.doppler import Doppler
from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DopplerDataUpdateCoordinator
from .const import DOMAIN
from .entity import DopplerEntity

_LOGGER = logging.getLogger(__name__)


@dataclass
class DopplerSwitchEntityDescription(SwitchEntityDescription):
    """Class to describe Doppler switch entities."""

    state_attr_name: str | None = None
    set_value_func_name: str | None = None
    is_on_attr_name: str | None = None


ENTITY_DESCRIPTIONS = [
    DopplerSwitchEntityDescription(
        "Blink Colon",
        name="Blink Colon",
        state_attr_name=ATTR_COLON_BLINK,
        set_value_func_name="set_colon_blink_mode",
    ),
    DopplerSwitchEntityDescription(
        "Use Colon",
        name="Use Colon",
        state_attr_name=ATTR_USE_COLON,
        set_value_func_name="set_use_colon_mode",
    ),
    DopplerSwitchEntityDescription(
        "Use Leading Zero",
        name="Use Leading Zero",
        state_attr_name=ATTR_USE_LEADING_ZERO,
        set_value_func_name="set_use_leading_zero_mode",
    ),
    DopplerSwitchEntityDescription(
        "Display Seconds",
        name="Display Seconds",
        state_attr_name=ATTR_DISPLAY_SECONDS,
        set_value_func_name="set_display_seconds_mode",
    ),
    DopplerSwitchEntityDescription(
        "Alexa: Ascending Alarms",
        name="Alexa Ascending Alarms",
        state_attr_name=ATTR_ALEXA_USE_ASCENDING_ALARMS,
        set_value_func_name="set_alexa_ascending_alarms_mode",
    ),
    DopplerSwitchEntityDescription(
        "Alexa: Tap to Talk Tone",
        name="Alexa Tap to Talk Tone",
        state_attr_name=ATTR_ALEXA_TAP_TO_TALK_TONE_ENABLED,
        set_value_func_name="set_alexa_tap_to_talk_tone_enabled",
    ),
    DopplerSwitchEntityDescription(
        "Alexa: Wake Word Tone",
        name="Alexa Wake Word Tone",
        state_attr_name=ATTR_ALEXA_WAKE_WORD_TONE_ENABLED,
        set_value_func_name="set_alexa_wake_word_tone_enabled",
    ),
    DopplerSwitchEntityDescription(
        "Volume Dependent EQ",
        name="Volume Dependent EQ",
        state_attr_name=ATTR_SOUND_PRESET_MODE,
        set_value_func_name="set_sound_preset_mode",
    ),
    DopplerSwitchEntityDescription(
        "Weather Service",
        name="Weather Service",
        state_attr_name=ATTR_WEATHER,
        set_value_func_name="set_weather_mode",
        is_on_attr_name="enabled",
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
                BaseDopplerSwitch(coordinator, entry, device, description)
                for description in ENTITY_DESCRIPTIONS
            ]
        )
    async_add_devices(entities)


class BaseDopplerSwitch(DopplerEntity, SwitchEntity):
    """Base class for Doppler switches."""

    _attr_device_class: SwitchDeviceClass.SWITCH

    def __init__(
        self,
        coordinator: DopplerDataUpdateCoordinator,
        entry: ConfigEntry,
        device: Doppler,
        description: DopplerSwitchEntityDescription,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, entry, device, description.name)
        self.entity_description: DopplerSwitchEntityDescription = description
        self._state_attr_name = description.state_attr_name
        self._set_value_func_name = description.set_value_func_name
        self._is_on_attr_name = description.is_on_attr_name

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        is_on = self.device_data[self._state_attr_name]
        if self._is_on_attr_name:
            getattr(is_on, self._is_on_attr_name)
        return is_on

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        self.device_data[self._state_attr_name] = await getattr(
            self.device, self._set_value_func_name
        )(**{self._is_on_attr_name: True} if self._is_on_attr_name else True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        self.device_data[self._state_attr_name] = await getattr(
            self.device, self._set_value_func_name
        )(**{self._is_on_attr_name: False} if self._is_on_attr_name else False)
