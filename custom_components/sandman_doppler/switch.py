"""Switch platform for Doppler Sandman."""
from __future__ import annotations

from collections.abc import Callable, Coroutine, Mapping
from dataclasses import asdict, dataclass
import functools
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
from doppyler.model.alarm import Alarm
from doppyler.model.doppler import Doppler

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

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
    # Note that while this is under Alexa in the api it's really not an Alexa function
    DopplerSwitchEntityDescription(
        "Ascending Alarms",
        name="Ascending Alarms",
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
        "Weather: Displayed",
        name="Weather: Displayed",
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
    """Setup switch platform."""

    @callback
    def async_add_device(device: Doppler) -> None:
        """Add Doppler switch entities."""
        coordinator: DopplerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
            device.dsn
        ]
        entities = [
            DopplerSwitch(coordinator, entry, device, description)
            for description in ENTITY_DESCRIPTIONS
        ]
        entities.extend(
            [
                DopplerAlarmSwitch(coordinator, entry, device, alarm)
                for alarm in device.alarms.values()
            ]
        )
        async_add_devices(entities)

        entry.async_on_unload(
            device.on_alarm_added(
                lambda alarm: async_add_devices(
                    [DopplerAlarmSwitch(coordinator, entry, device, alarm)]
                )
            )
        )
        entry.async_on_unload(
            device.on_alarm_removed(
                lambda alarm: async_dispatcher_send(
                    hass, f"{DOMAIN}_{device.dsn}_alarm_{alarm.id}_removed"
                )
            )
        )

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


class DopplerAlarmSwitch(CoordinatorEntity[DopplerDataUpdateCoordinator], SwitchEntity):
    """Doppler Alarm switch class."""

    _attr_device_class: SwitchDeviceClass.SWITCH
    _attr_has_entity_name = True
    _attr_icon = "mdi:alarm"

    def __init__(
        self,
        coordinator: DopplerDataUpdateCoordinator,
        config_entry: ConfigEntry,
        device: Doppler,
        alarm: Alarm,
    ):
        super().__init__(coordinator)
        self.config_entry = config_entry
        self.device = device
        self.alarm = alarm

        self._attr_unique_id = slugify(
            f"{self.config_entry.unique_id}_{self.device.dsn}_alarm_{alarm.id}"
        )
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, self.device.dsn)})

    @property
    def name(self) -> str:
        """Return the name of the alarm."""
        return f"Alarm {self.alarm.id} ({self.alarm.name})"

    @property
    def is_on(self) -> bool | None:
        return self.alarm.status in ("set", "snoozed", "active")

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return extra state attributes."""
        return asdict(self.alarm)

    async def _async_update_alarm_status(self, status: str) -> None:
        """Update the alarm status."""
        self.alarm.status = status
        await self.device.update_alarm(self.alarm.id, self.alarm)
        self.async_write_ha_state()

    async_turn_on = functools.partialmethod(_async_update_alarm_status, "set")
    async_turn_off = functools.partialmethod(_async_update_alarm_status, "unarmed")

    # async def async_turn_on(self, **kwargs) -> None:
    #     """Turn the switch on."""
    #     self.alarm.status = "set"
    #     await self.device.update_alarms([self.alarm])
    #     self.async_write_ha_state()

    # async def async_turn_off(self, **kwargs) -> None:
    #     """Turn the switch off."""
    #     self.alarm.status = "unarmed"
    #     await self.device.update_alarms([self.alarm])
    #     self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_{self.device.dsn}_alarm_{self.alarm.id}_removed",
                functools.partial(self.async_remove, force_remove=True),
            )
        )
