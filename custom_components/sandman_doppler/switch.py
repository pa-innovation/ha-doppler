"""Switch platform for Doppler Sandman."""
from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
import logging
from typing import Any

from doppyler.const import (
    ATTR_ALEXA_TAP_TO_TALK_TONE_ENABLED,
    ATTR_ALEXA_USE_ASCENDING_ALARMS,
    ATTR_ALEXA_WAKE_WORD_TONE_ENABLED,
    ATTR_COLON_BLINK,
    ATTR_DISPLAY_SECONDS,
    ATTR_SOUND_PRESET_MODE,
    ATTR_SYNC_BUTTON_AND_DISPLAY_BRIGHTNESS,
    ATTR_SYNC_BUTTON_AND_DISPLAY_COLOR,
    ATTR_SYNC_DAY_AND_NIGHT_COLOR,
    ATTR_USE_COLON,
    ATTR_USE_FADE_TIME,
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
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DopplerDataUpdateCoordinator
from .const import DOMAIN
from .entity import DopplerEntity

_LOGGER = logging.getLogger(__name__)


@dataclass
class DopplerSwitchEntityDescription(SwitchEntityDescription):
    """Class to describe Doppler switch entities."""

    state_key: str | None = None
    state_func: Callable[[Any], Any] = lambda x: x
    set_value_func: Callable[[Doppler, bool], Coroutine[Any, Any, bool]] = None
    set_value_func_name: str | None = None


ENTITY_DESCRIPTIONS = [
    DopplerSwitchEntityDescription(
        "Colon: Blink",
        name="Colon: Blink",
        state_key=ATTR_COLON_BLINK,
        set_value_func_name="set_colon_blink_mode",
    ),
    DopplerSwitchEntityDescription(
        "Colon: Show",
        name="Colon: Show",
        state_key=ATTR_USE_COLON,
        set_value_func_name="set_use_colon_mode",
    ),
    DopplerSwitchEntityDescription(
        "Fade Time Between Changes",
        name="Fade Time Between Changes",
        state_key=ATTR_USE_FADE_TIME,
        set_value_func_name="set_use_fade_time",
    ),
    DopplerSwitchEntityDescription(
        "Use Leading Zero",
        name="Use Leading Zero",
        state_key=ATTR_USE_LEADING_ZERO,
        set_value_func_name="set_use_leading_zero_mode",
    ),
    DopplerSwitchEntityDescription(
        "Display Seconds",
        name="Display Seconds",
        state_key=ATTR_DISPLAY_SECONDS,
        set_value_func_name="set_display_seconds_mode",
    ),
    DopplerSwitchEntityDescription(
        "Alexa: Ascending Alarms",
        name="Alexa: Ascending Alarms",
        state_key=ATTR_ALEXA_USE_ASCENDING_ALARMS,
        set_value_func_name="set_alexa_ascending_alarms_mode",
    ),
    DopplerSwitchEntityDescription(
        "Alexa: Tap to Talk Tone",
        name="Alexa: Tap to Talk Tone",
        state_key=ATTR_ALEXA_TAP_TO_TALK_TONE_ENABLED,
        set_value_func_name="set_alexa_tap_to_talk_tone_enabled",
    ),
    DopplerSwitchEntityDescription(
        "Alexa: Wake Word Tone",
        name="Alexa: Wake Word Tone",
        state_key=ATTR_ALEXA_WAKE_WORD_TONE_ENABLED,
        set_value_func_name="set_alexa_wake_word_tone_enabled",
    ),
    DopplerSwitchEntityDescription(
        "Volume Dependent EQ",
        name="Volume Dependent EQ",
        state_key=ATTR_SOUND_PRESET_MODE,
        set_value_func_name="set_sound_preset_mode",
    ),
    DopplerSwitchEntityDescription(
        "Weather Service",
        name="Weather Service",
        state_key=ATTR_WEATHER,
        state_func=lambda x: x.enabled,
        set_value_func=lambda dev, val: dev.set_weather_configuration(enabled=val),
    ),
    DopplerSwitchEntityDescription(
        "Sync: Button/Display Brightness",
        name="Sync: Button/Display Brightness",
        state_key=ATTR_SYNC_BUTTON_AND_DISPLAY_BRIGHTNESS,
        set_value_func_name="set_sync_button_display_brightness",
    ),
    DopplerSwitchEntityDescription(
        "Sync: Button/Display Color",
        name="Sync: Button/Display Color",
        state_key=ATTR_SYNC_BUTTON_AND_DISPLAY_COLOR,
        set_value_func_name="set_sync_button_display_color",
    ),
    DopplerSwitchEntityDescription(
        "Sync: Day/Night Color",
        name="Sync: Day/Night Color",
        state_key=ATTR_SYNC_DAY_AND_NIGHT_COLOR,
        set_value_func_name="set_sync_day_night_color",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
) -> None:
    """Setup sensor platform."""

    @callback
    def async_add_device(device: Doppler) -> None:
        """Add Doppler binary sensor entities."""
        coordinator: DopplerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
            device.dsn
        ]
        entities = [
            DopplerSwitch(coordinator, entry, device, description)
            for description in ENTITY_DESCRIPTIONS
        ]
        async_add_devices(entities)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, f"{DOMAIN}_{entry.entry_id}_device_added", async_add_device
        )
    )


class DopplerSwitch(DopplerEntity[DopplerSwitchEntityDescription], SwitchEntity):
    """Base class for Doppler switches."""

    _attr_device_class: SwitchDeviceClass.SWITCH
    _attr_entity_category = EntityCategory.CONFIG

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self.ed.state_func(self.device_data[self.ed.state_key])

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        if self.ed.set_value_func:
            new_val = await self.ed.set_value_func(self.device, True)
        else:
            new_val = await getattr(self.device, self.ed.set_value_func_name)(True)

        self.device_data[self.ed.state_key] = new_val
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        if self.ed.set_value_func:
            new_val = await self.ed.set_value_func(self.device, False)
        else:
            new_val = await getattr(self.device, self.ed.set_value_func_name)(False)

        self.device_data[self.ed.state_key] = new_val
        self.async_write_ha_state()
