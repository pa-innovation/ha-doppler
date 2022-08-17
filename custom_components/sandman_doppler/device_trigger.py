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

TRIGGER_TYPES = {"sandman_doppler_button_event"}

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),
    }
)


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, Any]]:
    """List device triggers for sandman_doppler devices."""
    registry = entity_registry.async_get(hass)
    device_registry = dr.async_get(hass)
    triggers = []

    _LOGGER.warning(f"device_id={device_id}")

    device_entry = device_registry.async_get(str(device_id))
    assert device_entry
    _LOGGER.warning(f"device_entry.identifiers={device_entry.identifiers}")

    # for id in device_entry.identifiers:
    #     if id[1].startswith("Doppler"):
    #         dsn = id[1]
#    dsn = "test"

#    for i in range(1, 3):
#        triggers.append(
#            {
#                CONF_PLATFORM: "device",
#                CONF_DOMAIN: "sandman_doppler",
#                CONF_DEVICE_ID: device_id,
#                ATTR_DSN: dsn,
#                ATTR_BUTTON: i,
#                CONF_TYPE: "Doppler-4fcd8f3c_butt_1",
#                CONF_SUBTYPE: i,
#            }
#        )

#    _LOGGER.warning(f"triggers= {triggers}")

    return [
        {
            CONF_PLATFORM: "device",
            CONF_DOMAIN: DOMAIN,
            CONF_DEVICE_ID: device_id,
#            ATTR_DSN: dsn,
#            ATTR_BUTTON: 1,
            CONF_TYPE: "sandman_doppler_button_event",
#            CONF_SUBTYPE: "1",
        }
    ]


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: AutomationActionType,
    automation_info: AutomationTriggerInfo,
) -> CALLBACK_TYPE:
    """Attach a trigger."""

    #    my_device_registry=dr.async_get(hass)
    #    device=my_device_registry.async_get(config[CONF_DEVICE_ID])

    #    for id in device.identifiers:
    #        if id.startswith("Doppler"):
    #            dsn=id

    event_config = event_trigger.TRIGGER_SCHEMA({
            event_trigger.CONF_PLATFORM: "event",
            event_trigger.CONF_EVENT_TYPE: "sandman_doppler_button_event",
            #        event_trigger.CONF_EVENT_DATA: {
            #            ATTR_DSN: dsn,
            #            ATTR_BUTTON: {"button1","button2"},
            #            CONF_DEVICE_ID: config[CONF_DEVICE_ID],
            #            CONF_TYPE: config[CONF_TYPE],
            #        },
        })

    _LOGGER.warning(f"event_config={event_config}")

    return await event_trigger.async_attach_trigger(
        hass, event_config, action, automation_info, platform_type="device"
    )
