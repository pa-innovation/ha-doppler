"""Siren platform for Doppler Sandman."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
import logging
from random import randint
from typing import Any

from doppyler.const import ATTR_ALARM_SOUNDS
from doppyler.exceptions import InvalidDataReturned
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


async def _ok_is_success(coro: Coroutine[Any, Any, None]) -> None:
    """Await a sound call, treating a plain-text "OK" reply as success.

    Firmware 0.1714 answers a successful alarms/sounds/play request with
    HTTP 200 and the body "OK". doppyler raises InvalidDataReturned for any
    200 reply that isn't JSON, so the call fails even though the sound plays.
    Any other non-JSON reply still raises.
    """
    try:
        await coro
    except InvalidDataReturned as err:
        if not err.args or str(err.args[0]).strip() != "OK":
            raise


@dataclass
class DopplerSirenEntityDescription(SirenEntityDescription):
    """Class to describe Doppler siren entities."""

    available_tones_key: str = None
    turn_on_func: Callable[[Doppler, str, int | None], Coroutine[Any, Any, None]] = None
    turn_off_func: Callable[[Doppler, int], Coroutine[Any, Any, None]] = None


SIREN_ENTITY_DESCRIPTIONS = [
    DopplerSirenEntityDescription(
        "Alarm",
        name="Alarm",
        icon="mdi:alarm",
        available_tones_key=ATTR_ALARM_SOUNDS,
        turn_on_func=lambda dev, sound, volume: dev.play_alarm_sound(sound, volume),
        # Doppler.stop_alarm_sound() sends {"sound": "stop"} without "vol", which
        # firmware 0.1714 rejects with 404 "alarm not found" (like a play request
        # without "vol"), so send the stop through play_alarm_sound with a volume.
        turn_off_func=lambda dev, volume: dev.play_alarm_sound("stop", volume),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
) -> None:
    """Setup siren platform."""

    @callback
    def async_add_device(device: Doppler) -> None:
        """Add Doppler siren entities."""
        coordinator: DopplerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
            device.dsn
        ]
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
        if self.ed.available_tones_key is None:
            return []
        tones = self.device_data.get(self.ed.available_tones_key)
        if tones is None:
            return []
        return sorted(tones)

    @property
    def _clock_volume(self) -> int:
        """Return the clock's own volume setting (0-100), defaulting to 50."""
        return int(self.device_data.get(ATTR_VOLUME_LEVEL) or 50)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the siren on."""
        sound: str | None = kwargs.get(ATTR_TONE)
        if sound is None:
            tones = self.available_tones
            if not tones:
                _LOGGER.warning("No tones available, cannot turn on siren")
                return
            idx = randint(0, len(tones) - 1)
            sound = tones[idx]
            _LOGGER.info("No sound specified, picking a random one: %s", sound)
        # The clock needs "vol" as an integer 0-100: a float is rejected
        # (HTTP 500) and a request without "vol" fails with 404 "alarm not
        # found". HA's volume_level is 0-1, so scale it, and fall back to the
        # clock's own volume setting when none is given.
        level: float | None = kwargs.get(ATTR_VOLUME_LEVEL)
        if level is not None:
            volume = max(1, min(100, round(level * 100)))
        else:
            volume = self._clock_volume
        await _ok_is_success(self.ed.turn_on_func(self.device, sound, volume))

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the siren off."""
        await _ok_is_success(self.ed.turn_off_func(self.device, self._clock_volume))
