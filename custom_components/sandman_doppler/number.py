"""Number platform for Doppler Sandman."""
from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
import logging
from typing import Any

from doppyler.const import (
    ATTR_DAY_TO_NIGHT_TRANSITION_VALUE,
    ATTR_NIGHT_TO_DAY_TRANSITION_VALUE,
    ATTR_TIME_OFFSET,
    ATTR_VOLUME_LEVEL,
)
from doppyler.model.doppler import Doppler
from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DopplerDataUpdateCoordinator
from .const import DOMAIN
from .entity import DopplerEntity

_LOGGER = logging.getLogger(__name__)


@dataclass
class DopplerNumberEntityDescription(NumberEntityDescription):
    """Class to describe Doppler number entities."""

    state_key: str | None = None
    state_func: Callable[[Any], int] = lambda x: x
    set_value_func: Callable[[Doppler, int], Coroutine[Any, Any, int]] | None = None
    mode: NumberMode = NumberMode.AUTO


NUMBER_ENTITY_DESCRIPTIONS = [
    DopplerNumberEntityDescription(
        "Volume Level",
        name="Volume Level",
        icon="mdi:volume-high",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
        native_unit_of_measurement=PERCENTAGE,
        state_key=ATTR_VOLUME_LEVEL,
        set_value_func=lambda dev, val: dev.set_volume_level(int(val)),
    ),
    DopplerNumberEntityDescription(
        "Time Offset",
        name="Time Offset",
        icon="mdi:clock",
        native_min_value=-60,
        native_max_value=60,
        native_step=1,
        mode=NumberMode.BOX,
        native_unit_of_measurement="min",
        entity_category=EntityCategory.CONFIG,
        state_key=ATTR_TIME_OFFSET,
        state_func=lambda x: x.total_seconds() // 60,
        set_value_func=lambda dev, val: dev.set_offset(int(val)),
    ),
    DopplerNumberEntityDescription(
        "Day to Night Transition",
        name="Day to Night Transition",
        icon="mdi:weather-night",
        native_min_value=0,
        native_max_value=65535,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        state_key=ATTR_DAY_TO_NIGHT_TRANSITION_VALUE,
        set_value_func=lambda dev, val: dev.set_day_to_night_transition_value(val),
    ),
    DopplerNumberEntityDescription(
        "Night to Day Transition",
        name="Night to Day Transition",
        icon="mdi:weather-sunny",
        native_min_value=0,
        native_max_value=65535,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        state_key=ATTR_NIGHT_TO_DAY_TRANSITION_VALUE,
        set_value_func=lambda dev, val: dev.set_night_to_day_transition_value(val),
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
            DopplerNumber(coordinator, entry, device, description)
            for description in NUMBER_ENTITY_DESCRIPTIONS
        ]
        async_add_devices(entities)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, f"{DOMAIN}_{entry.entry_id}_device_added", async_add_device
        )
    )


class DopplerNumber(DopplerEntity[DopplerNumberEntityDescription], NumberEntity):
    """Doppler Number Entity."""

    @property
    def mode(self) -> NumberMode:
        """Return number mode."""
        return self.ed.mode

    @property
    def native_value(self) -> int:
        """Return the value of the number."""
        return self.ed.state_func(self.device_data[self.ed.state_key])

    async def async_set_native_value(self, value: int) -> None:
        """Set the value of the number."""
        self.device_data[self.ed.state_key] = await self.ed.set_value_func(
            self.device, value
        )
