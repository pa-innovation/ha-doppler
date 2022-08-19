"""Button platform for Doppler Sandman."""
from __future__ import annotations

import logging
from typing import Any


from homeassistant.components.button import (
    ButtonEntity,
    ButtonEntityDescription,
)


from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DopplerDataUpdateCoordinator

from .entity import DopplerEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
) -> None:
     coordinator: DopplerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for device in coordinator.api.devices.values():
        entities.extend(
            [
                DopplerButton1(coordinator, entry, device, "Doppler Button 1"),
                DopplerButton2(coordinator, entry, device, "Doppler Button 2"),
            ]
        )
    async_add_devices(entities)

class DopplerButton1(DopplerEntity,ButtonEntity):


    def press(self):
        _LOGGER.warning("Button 1 Pressed")


class DopplerButton2(DopplerEntity,ButtonEntity):


    def press(self):
        _LOGGER.warning("Button 2 Pressed")

    
