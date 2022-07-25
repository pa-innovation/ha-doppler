"""Switch platform for Doppler Sandman."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DopplerDataUpdateCoordinator
from .const import (
    ATTR_COLON_BLINK,
    ATTR_USE_COLON,
    ATTR_USE_LEADING_ZERO,
    ATTR_DISPLAY_SECONDS,
    ATTR_ALEXA_USE_ASCENDING_ALARMS,
    ATTR_ALEXA_USE_TAPTALK_TONE,
    DOMAIN
)
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
                ColonBlinkSwitch(coordinator, entry, device, "Blink Colon"),
                UseColonSwitch(coordinator, entry, device, "Use Colon"),
                UseLeadingZeroSwitch(coordinator, entry, device, "Use Leading Zero"),
                UseDisplaySecondsSwitch(coordinator, entry, device, "Display Seconds"),
                UseAscendingAlarmsSwitch(coordinator, entry, device, "Alexa Use Ascending Alarms"),
                UseTapTalkToneSwitch(coordinator, entry, device, "Alexa Tap to Talk Tone"),
            ]
        )
    async_add_devices(entities)


class ColonBlinkSwitch(DopplerEntity, SwitchEntity):
    """Doppler ColonBlink class."""
    _attr_device_class="switch"

    async def async_turn_on(self, **kwargs):
        """Turn Colon Blinking On"""
        await self.coordinator.api.set_colon_blink_mode(
            self.device, True)


    async def async_turn_off(self, **kwargs):
        """Turn Colon Blink Off"""
        await self.coordinator.api.set_colon_blink_mode(
            self.device, False)
        

    @property
    def is_on(self):
        """Return true if device is on."""
        return self.coordinator.data[self.device.name][ATTR_COLON_BLINK]


class UseColonSwitch(DopplerEntity, SwitchEntity):
    """Doppler UseColon class."""
    _attr_device_class="switch"

    async def async_turn_on(self, **kwargs):
        """Turn Colon On"""
        await self.coordinator.api.set_use_colon_mode(
            self.device, True)


    async def async_turn_off(self, **kwargs):
        """Turn Colon Off"""
        await self.coordinator.api.set_use_colon_mode(
            self.device, False)
        

    @property
    def is_on(self):
        """Return true if device is on."""
        return self.coordinator.data[self.device.name][ATTR_USE_COLON]


class UseLeadingZeroSwitch(DopplerEntity, SwitchEntity):
    """Doppler UseLeadingZero class."""
    _attr_device_class="switch"

    async def async_turn_on(self, **kwargs):
        """Turn Colon On"""
        await self.coordinator.api.set_use_leading_zero_mode(
            self.device, True)


    async def async_turn_off(self, **kwargs):
        """Turn Colon Off"""
        await self.coordinator.api.set_use_leading_zero_mode(
            self.device, False)
        

    @property
    def is_on(self):
        """Return true if device is on."""
        return self.coordinator.data[self.device.name][ATTR_USE_LEADING_ZERO]



class UseDisplaySecondsSwitch(DopplerEntity, SwitchEntity):
    """Doppler UseLeadingZero class."""
    _attr_device_class="switch"

    async def async_turn_on(self, **kwargs):
        """Turn Colon On"""
        await self.coordinator.api.set_display_seconds_mode(
            self.device, True)


    async def async_turn_off(self, **kwargs):
        """Turn Colon Off"""
        await self.coordinator.api.set_display_seconds_mode(
            self.device, False)
        

    @property
    def is_on(self):
        """Return true if device is on."""
        return self.coordinator.data[self.device.name][ATTR_DISPLAY_SECONDS]


class UseAscendingAlarmsSwitch(DopplerEntity, SwitchEntity):
    """Doppler UseAscendingAlarms class."""
    _attr_device_class="switch"

    async def async_turn_on(self, **kwargs):
        """Turn Colon On"""
        await self.coordinator.api.set_alexa_ascending_alarms_mode(
            self.device, True)


    async def async_turn_off(self, **kwargs):
        """Turn Colon Off"""
        await self.coordinator.api.set_alexa_ascending_alarms_mode(
            self.device, False)
        

    @property
    def is_on(self):
        """Return true if device is on."""
        return self.coordinator.data[self.device.name][ATTR_ALEXA_USE_ASCENDING_ALARMS]


class UseTapTalkToneSwitch(DopplerEntity, SwitchEntity):
    """Doppler UseTapTalkTone class."""
    _attr_device_class="switch"

    async def async_turn_on(self, **kwargs):
        """Turn Colon On"""
        await self.coordinator.api.set_alexa_taptalk_tone_mode(
            self.device, True)


    async def async_turn_off(self, **kwargs):
        """Turn Colon Off"""
        await self.coordinator.api.set_alexa_taptalk_tone_mode(
            self.device, False)
        

    @property
    def is_on(self):
        """Return true if device is on."""
        return self.coordinator.data[self.device.name][ATTR_ALEXA_USE_TAPTALK_TONE]

    
