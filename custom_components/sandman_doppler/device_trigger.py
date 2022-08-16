"""Provides device triggers for sandman_doppler."""
from __future__ import annotations

from typing import Any
import logging
_LOGGER: logging.Logger = logging.getLogger(__package__)

import voluptuous as vol

from homeassistant.components.automation import (
    AutomationActionType,
    AutomationTriggerInfo,
)
from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_ENTITY_ID,
    CONF_PLATFORM,
    CONF_TYPE,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_registry
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

# TODO specify your supported trigger types.
TRIGGER_TYPES = {"Doppler-4fcd8f3c_butt_1", "Doppler-4fcd8f3c_butt2"}

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
#        vol.Required(CONF_ENTITY_ID): cv.entity_id,
        vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),
    }
)


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, Any]]:
    """List device triggers for sandman_doppler devices."""
    registry = entity_registry.async_get(hass)
    device_registry=dr.async_get(hass)
    triggers = []

    # TODO Read this comment and remove it.
    # This example shows how to iterate over the entities of this device
    # that match this integration. If your triggers instead rely on
    # events fired by devices without entities, do something like:
    # zha_device = await _async_get_zha_device(hass, device_id)
    # return zha_device.device_triggers

    # Get all the integrations entities for this device
    #for entry in entity_registry.async_entries_for_device(registry, device_id):
    #    if entry.domain != DOMAIN:
    #        continue

        # Add triggers for each entity that belongs to this integration
        # TODO add your own triggers.
    _LOGGER.warning(f"device_id={device_id}")


    device_entry=dr.async_get(str(device_id))
    _LOGGER.warning(f"device_entry.identifiers={device_entry.identifiers}")

    
    
    triggers.append({
        # Required fields of TRIGGER_BASE_SCHEMA
        CONF_PLATFORM: "device",
        CONF_DOMAIN: "sandman_doppler",
        CONF_DEVICE_ID: device_id,
        # Required fields of TRIGGER_SCHEMA
        CONF_TYPE: "Doppler-4fcd8f3c_butt_1",
    })

    _LOGGER.warning(f"triggers= {triggers}")

    return triggers


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: AutomationActionType,
    automation_info: AutomationTriggerInfo,
) -> CALLBACK_TYPE:
    """Attach a trigger."""

    event_config = event_trigger.TRIGGER_SCHEMA({
        event_trigger.CONF_PLATFORM: "event",
        event_trigger.CONF_EVENT_TYPE: "Doppler-4fcd8f3c_butt_1"
    })
                                                
    _LOGGER.warning(f"event_config={event_config}")
            
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, automation_info, platform_type="device"
    )
