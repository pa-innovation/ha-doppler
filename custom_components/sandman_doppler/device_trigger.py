"""Provides device triggers for sandman_doppler."""
from __future__ import annotations

from typing import Any

from homeassistant.components.automation import (
    AutomationActionType,
    AutomationTriggerInfo,
)
from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import (
    ATTR_DEVICE_ID,
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_PLATFORM,
    CONF_TYPE,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from .const import ATTR_BUTTON, CONF_SUBTYPE, DOMAIN, EVENT_BUTTON_PRESSED

TRIGGER_TYPES = {EVENT_BUTTON_PRESSED}

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),
        vol.Required(ATTR_BUTTON): vol.All(vol.Coerce(int), vol.Range(min=1, max=2)),
        vol.Required(CONF_SUBTYPE): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=2), vol.Coerce(str)
        ),
    }
)


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, Any]]:
    """List device triggers for sandman_doppler devices."""
    device_registry = dr.async_get(hass)
    triggers = []

    device_entry = device_registry.async_get(device_id)
    if not device_entry:
        raise ValueError(f"Device not found: {device_id}")

    if not any(id[0] == DOMAIN for id in device_entry.identifiers):
        raise ValueError(f"Device {device_id} is not a sandman_doppler device")

    triggers.extend(
        [
            {
                CONF_PLATFORM: "device",
                CONF_DOMAIN: DOMAIN,
                CONF_DEVICE_ID: device_id,
                ATTR_BUTTON: i,
                CONF_TYPE: EVENT_BUTTON_PRESSED,
                CONF_SUBTYPE: i,
            }
            for i in range(1, 3)
        ]
    )

    return triggers


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: AutomationActionType,
    automation_info: AutomationTriggerInfo,
) -> CALLBACK_TYPE:
    """Attach a trigger."""

    if config[CONF_TYPE] in TRIGGER_TYPES:
        event_config = event_trigger.TRIGGER_SCHEMA(
            {
                event_trigger.CONF_PLATFORM: "event",
                event_trigger.CONF_EVENT_TYPE: EVENT_BUTTON_PRESSED,
                event_trigger.CONF_EVENT_DATA: {
                    ATTR_DEVICE_ID: config[CONF_DEVICE_ID],
                    ATTR_BUTTON: config[ATTR_BUTTON],
                },
            }
        )

        return await event_trigger.async_attach_trigger(
            hass, event_config, action, automation_info, platform_type="device"
        )

    raise ValueError(f"Unsupported trigger type {config[CONF_TYPE]}")
