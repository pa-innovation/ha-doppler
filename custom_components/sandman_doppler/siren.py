"""Siren platform for Doppler Sandman."""
from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
import logging
from random import randint
from typing import Any

from doppyler.const import ATTR_ALARM_SOUNDS
from doppyler.model.doppler import Doppler
from homeassistant.components.siren import (
    ATTR_TONE,
    ATTR_VOLUME_LEVEL,
    SirenEntity,
    SirenEntityDescription,
    SirenEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DopplerDataUpdateCoordinator
from .const import DOMAIN
from .entity import DopplerEntity

_LOGGER = logging.getLogger(__name__)


@dataclass
class DopplerSirenEntityDescription(SirenEntityDescription):
    """Class to describe Doppler siren entities."""

    available_tones_key: str = None
    turn_on_func: Callable[[Doppler, str, int | None], Coroutine[Any, Any, None]] = None
    turn_off_func: Callable[[Doppler], Coroutine[Any, Any, None]] = None


SIREN_ENTITY_DESCRIPTIONS = [
    DopplerSirenEntityDescription(
        "Alarm",
        name="Alarm",
        icon="mdi:volume-high",
        available_tones_key=ATTR_ALARM_SOUNDS,
        turn_on_func=lambda dev, sound, volume: dev.play_alarm_sound(sound, volume),
        turn_off_func=lambda dev: dev.stop_alarm_sound(),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
) -> None:
    """Setup sensor platform."""

    @callback
    def async_add_device(device: Doppler) -> None:
        """Add Doppler binary sensor entities."""
        coordinator: DopplerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
        entities = [
            DopplerSiren(coordinator, entry, device, description)
            for description in SIREN_ENTITY_DESCRIPTIONS
        ]
        async_add_devices(entities)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, f"{DOMAIN}_{entry.entry_id}_device_added", async_add_device
        )
    )


class DopplerSiren(DopplerEntity[DopplerSirenEntityDescription], SirenEntity):
    """Doppler Siren Entity."""

    @property
    def supported_features(self) -> int | None:
        return (
            SirenEntityFeature.TONES
            | SirenEntityFeature.TURN_OFF
            | SirenEntityFeature.TURN_ON
            | SirenEntityFeature.VOLUME_SET
        )

    @property
    def available_tones(self) -> list[str]:
        """Return a list of available tones."""
        return sorted(self.device_data[self.ed.available_tones_key])

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the siren on."""
        sound: str | None = kwargs.get(ATTR_TONE)
        if sound is None:
            idx = randint(0, len(self.available_tones) - 1)
            sound = self.available_tones[idx]
            _LOGGER.info("No sound specified, picking a random one: %s", sound)
        volume: int | None = kwargs.get(ATTR_VOLUME_LEVEL)
        await self.ed.turn_on_func(self.device, sound, volume)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the siren off."""
        await self.ed.turn_off_func(self.device)
