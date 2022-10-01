"""The Sandman Doppler services module."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import functools
import logging
from typing import Any

from doppyler.client import DopplerClient
from doppyler.const import (
    ATTR_COLOR,
    ATTR_COLORS,
    ATTR_DEVICES,
    ATTR_DIRECTION,
    ATTR_DURATION,
    ATTR_ENABLED,
    ATTR_GAP,
    ATTR_ID,
    ATTR_LOCATION,
    ATTR_NAME,
    ATTR_NUMBER,
    ATTR_RAINBOW,
    ATTR_REPEAT,
    ATTR_SIZE,
    ATTR_SOUND,
    ATTR_SPARKLE,
    ATTR_SPEED,
    ATTR_TEXT,
    ATTR_VOLUME,
)
from doppyler.model.alarm import Alarm, AlarmSource, RepeatDayOfWeek
from doppyler.model.color import Color
from doppyler.model.doppler import Doppler
from doppyler.model.light_bar import Direction, LightBarDisplayEffect, Mode, Sparkle
from doppyler.model.main_display_text import MainDisplayText
from doppyler.model.mini_display_number import MiniDisplayNumber
from homeassistant.const import ATTR_AREA_ID, ATTR_DEVICE_ID, ATTR_ENTITY_ID, ATTR_TIME
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.helpers.service import ServiceCall
import voluptuous as vol

from .const import DOMAIN

SCAN_INTERVAL = timedelta(seconds=60)

_LOGGER = logging.getLogger(__name__)

COLOR_SCHEMA = vol.All(
    [vol.All(vol.Coerce(int), vol.Range(0, 255))],
    vol.Length(3, 3),
    lambda x: Color.from_list(x),
)
BASE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_AREA_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
    }
)

LIGHT_BAR_BASE_SCHEMA = BASE_SCHEMA.extend(
    {
        vol.Optional(ATTR_COLOR): COLOR_SCHEMA,
        vol.Optional(ATTR_COLORS): vol.All(cv.ensure_list, [COLOR_SCHEMA]),
        vol.Required(ATTR_DURATION): cv.time_period,
        vol.Optional(ATTR_SPARKLE): vol.Coerce(Sparkle),
        vol.Optional(ATTR_RAINBOW): cv.boolean,
    }
)
LIGHT_BAR_SET_EACH_SCHEMA = LIGHT_BAR_BASE_SCHEMA

LIGHT_BAR_SET_SCHEMA = LIGHT_BAR_BLINK_SCHEMA = LIGHT_BAR_BASE_SCHEMA.extend(
    {
        vol.Optional(ATTR_SPEED): vol.All(vol.Coerce(int), vol.Range(min=0)),
    }
)


async def call_doppyler_api_across_devices(
    devices: set[Doppler], func_name: str, *args, **kwargs
) -> None:
    """Call Doppyler API across all devices."""
    results = await asyncio.gather(
        *(getattr(device, func_name)(*args, **kwargs) for device in devices),
        return_exceptions=True,
    )
    if errors := [
        tup for tup in zip(devices, results) if isinstance(tup[1], Exception)
    ]:
        lines = (
            f"{len(errors)} error(s):",
            *(
                f"{device} - {type(error).__name__}: {error}"
                for device, error in errors
            ),
        )
        raise HomeAssistantError("\n".join(lines))


def _validate_colors(data: dict[str, Any]) -> dict[str, Any]:
    """Validate colors in service call dict."""
    cv.has_at_least_one_key(ATTR_RAINBOW, ATTR_COLOR, ATTR_COLORS)(data)
    single_color = data.pop(ATTR_COLOR, None)

    if data.get(ATTR_RAINBOW) and (single_color or data.get(ATTR_COLORS)):
        _LOGGER.warning("'rainbow' supercedes color choices, removing")
        data.pop(ATTR_COLORS, None)

    if single_color and not data.get(ATTR_COLORS):
        data[ATTR_COLORS] = [single_color]

    return data


class DopplerServices:
    """Class to represent Sandman Doppler integration services."""

    def __init__(
        self,
        hass: HomeAssistant,
        ent_reg: er.EntityRegistry,
        dev_reg: dr.DeviceRegistry,
        client: DopplerClient,
    ) -> None:
        """Initialize services."""
        self.hass = hass
        self.ent_reg = ent_reg
        self.dev_reg = dev_reg
        self.client = client

    @callback
    def get_dopplers_from_targets(self, data: dict[str, Any]) -> dict[str, Any]:
        """Get dopplers from service targets."""
        devices: set[Doppler] = set()
        device_ids: set[str] = set()
        device_ids.update(data.get(ATTR_DEVICE_ID, []))
        device_ids.update(
            {
                entity_entry.device_id
                for entity_id in data.get(ATTR_ENTITY_ID, [])
                if (entity_entry := self.ent_reg.async_get(entity_id))
                and entity_entry.device_id
            }
        )
        device_ids.update(
            {
                dev.id
                for area_id in data.get(ATTR_AREA_ID, [])
                for dev in dr.async_entries_for_area(self.dev_reg, area_id)
            }
        )

        for device_id in device_ids:
            if not (device_entry := self.dev_reg.async_get(device_id)):
                continue
            identifier = next(id for id in device_entry.identifiers)
            if identifier[0] != DOMAIN:
                _LOGGER.warning(
                    "Skipping device %s for service call because it is not a supported "
                    "Sandman Doppler device"
                )
                continue
            devices.add(self.client.devices[identifier[1]])

        if not devices:
            raise vol.Invalid("No devices found in given targets!")

        data[ATTR_DEVICES] = devices
        return data

    def _expand_schema(self, schema: dict[vol.Marker, Any]) -> vol.Schema:
        """Get expanded schema from service specific schema."""
        return vol.All(
            BASE_SCHEMA.extend(schema),
            cv.has_at_least_one_key(ATTR_DEVICE_ID, ATTR_ENTITY_ID, ATTR_AREA_ID),
            self.get_dopplers_from_targets,
        )

    def _get_light_bar_schema(self, schema: dict[vol.Marker, Any]) -> vol.Schema:
        """Get schema for light bar service specific schema."""
        return vol.All(
            schema,
            cv.has_at_least_one_key(ATTR_DEVICE_ID, ATTR_ENTITY_ID, ATTR_AREA_ID),
            _validate_colors,
            self.get_dopplers_from_targets,
        )

    @callback
    def async_register(self):
        """Register services."""
        self.hass.services.async_register(
            DOMAIN,
            "set_weather_location",
            self.handle_set_weather_location,
            schema=self._expand_schema({vol.Required(ATTR_LOCATION): cv.string}),
        )

        self.hass.services.async_register(
            DOMAIN,
            "add_alarm",
            self.handle_add_alarm,
            schema=self._expand_schema(
                {
                    vol.Required(ATTR_ID): vol.Coerce(int),
                    vol.Required(ATTR_NAME): cv.string,
                    vol.Required(ATTR_TIME): cv.time,
                    vol.Required(ATTR_REPEAT, default=[]): vol.All(
                        cv.ensure_list, [vol.Coerce(RepeatDayOfWeek)]
                    ),
                    vol.Required(ATTR_COLOR): COLOR_SCHEMA,
                    vol.Required(ATTR_VOLUME): vol.All(
                        vol.Coerce(int), vol.Range(1, 100)
                    ),
                    vol.Required(ATTR_ENABLED): cv.boolean,
                    vol.Required(ATTR_SOUND): cv.string,
                }
            ),
        )

        self.hass.services.async_register(
            DOMAIN,
            "delete_alarm",
            self.handle_delete_alarm,
            schema=self._expand_schema({vol.Required(ATTR_ID): vol.Coerce(int)}),
        )

        self.hass.services.async_register(
            DOMAIN,
            "set_main_display_text",
            self.handle_set_main_display,
            schema=self._expand_schema(
                {
                    vol.Required(ATTR_TEXT): vol.All(
                        cv.string, cv.matches_regex(r"(?![kmwv])[a-z0-9 \_\-]+")
                    ),
                    vol.Required(ATTR_SPEED): vol.Coerce(int),
                    vol.Required(ATTR_DURATION): cv.time_period,
                    vol.Required(ATTR_COLOR): COLOR_SCHEMA,
                }
            ),
        )

        self.hass.services.async_register(
            DOMAIN,
            "set_mini_display_number",
            self.handle_set_mini_display,
            schema=self._expand_schema(
                {
                    vol.Optional(ATTR_NUMBER): vol.Coerce(int),
                    vol.Optional(ATTR_DURATION): cv.time_period,
                    vol.Optional(ATTR_COLOR): COLOR_SCHEMA,
                }
            ),
        )

        self.hass.services.async_register(
            DOMAIN,
            "activate_light_bar_blink",
            functools.partial(self.handle_activate_light_bar, Mode.BLINK),
            schema=self._get_light_bar_schema(LIGHT_BAR_BLINK_SCHEMA),
        )

        self.hass.services.async_register(
            DOMAIN,
            "activate_light_bar_comet",
            functools.partial(self.handle_activate_light_bar, Mode.COMET),
            schema=self._get_light_bar_schema(
                LIGHT_BAR_BASE_SCHEMA.extend(
                    {
                        vol.Optional(ATTR_SPEED): vol.All(
                            vol.Coerce(int), vol.Range(min=0)
                        ),
                        vol.Optional(ATTR_SIZE): vol.All(
                            vol.Coerce(int), vol.Range(min=1, max=255)
                        ),
                        vol.Optional(ATTR_DIRECTION): vol.Coerce(Direction),
                    }
                )
            ),
        )

        self.hass.services.async_register(
            DOMAIN,
            "activate_light_bar_pulse",
            functools.partial(self.handle_activate_light_bar, Mode.PULSE),
            schema=self._get_light_bar_schema(
                LIGHT_BAR_BASE_SCHEMA.extend(
                    {
                        vol.Optional(ATTR_SPEED): vol.All(
                            vol.Coerce(int), vol.Range(min=0)
                        ),
                        vol.Optional(ATTR_GAP): vol.All(
                            vol.Coerce(int), vol.Range(min=2)
                        ),
                    }
                )
            ),
        )

        self.hass.services.async_register(
            DOMAIN,
            "activate_light_bar_set",
            functools.partial(self.handle_activate_light_bar, Mode.SET),
            schema=self._get_light_bar_schema(LIGHT_BAR_SET_SCHEMA),
        )

        self.hass.services.async_register(
            DOMAIN,
            "activate_light_bar_set_each",
            functools.partial(self.handle_activate_light_bar, Mode.SET_EACH),
            schema=self._get_light_bar_schema(LIGHT_BAR_BASE_SCHEMA),
        )

        self.hass.services.async_register(
            DOMAIN,
            "activate_light_bar_sweep",
            functools.partial(self.handle_activate_light_bar, Mode.SWEEP),
            schema=self._get_light_bar_schema(
                LIGHT_BAR_BASE_SCHEMA.extend(
                    {
                        vol.Optional(ATTR_SPEED): vol.All(
                            vol.Coerce(int), vol.Range(min=0)
                        ),
                        vol.Optional(ATTR_SIZE): vol.All(
                            vol.Coerce(int), vol.Range(min=1, max=255)
                        ),
                        vol.Optional(ATTR_DIRECTION): vol.Coerce(Direction),
                        vol.Optional(ATTR_GAP): vol.All(
                            vol.Coerce(int), vol.Range(min=0, max=255)
                        ),
                    }
                )
            ),
        )

    async def handle_set_weather_location(self, call: ServiceCall) -> None:
        """Handle set_weather_location service."""
        _LOGGER.warning(f"Called set_weather_location service")
        devices: set[Doppler] = call.data[ATTR_DEVICES]
        call_doppyler_api_across_devices(
            devices, "set_weather_configuration", location=call.data[ATTR_LOCATION]
        )

    async def handle_add_alarm(self, call: ServiceCall) -> None:
        """Handle add_alarm service."""
        _LOGGER.warning(f"Called add_alarm service")
        alarm = Alarm(
            id=call.data[ATTR_ID],
            name=call.data[ATTR_NAME],
            alarm_time=call.data[ATTR_TIME],
            repeat=call.data[ATTR_REPEAT],
            color=call.data[ATTR_COLOR],
            volume=call.data[ATTR_VOLUME],
            status=call.data[ATTR_ENABLED],
            src=AlarmSource.APP,
            sound=call.data[ATTR_SOUND],
        )
        devices: set[Doppler] = call.data[ATTR_DEVICES]
        await call_doppyler_api_across_devices(devices, "add_alarm", alarm)

    async def handle_delete_alarm(self, call: ServiceCall) -> None:
        """Handle delete_alarm service."""
        _LOGGER.warning(f"Called delete_alarm service")
        devices: set[Doppler] = call.data[ATTR_DEVICES]
        await call_doppyler_api_across_devices(
            devices, "delete_alarm", call.data[ATTR_ID]
        )

    async def handle_set_main_display(self, call: ServiceCall) -> None:
        """Handle set_main_display service."""
        _LOGGER.warning(f"Called set_main_display service")
        mdt = MainDisplayText(
            text=call.data[ATTR_TEXT],
            duration=call.data[ATTR_DURATION],
            speed=call.data[ATTR_SPEED],
            color=call.data[ATTR_COLOR],
        )
        devices: set[Doppler] = call.data[ATTR_DEVICES]
        await call_doppyler_api_across_devices(devices, "set_main_display_text", mdt)

    async def handle_set_mini_display(self, call: ServiceCall) -> None:
        """Handle set_mini_display service."""
        _LOGGER.warning(f"Called display_num_mini service")
        mdn = MiniDisplayNumber(
            number=call.data[ATTR_NUMBER],
            duration=call.data[ATTR_DURATION],
            color=call.data[ATTR_COLOR],
        )
        devices: set[Doppler] = call.data[ATTR_DEVICES]
        await call_doppyler_api_across_devices(devices, "set_mini_display_number", mdn)

    async def handle_activate_light_bar(self, mode: Mode, call: ServiceCall) -> None:
        """Handle activate_light_bar_* services."""
        _LOGGER.warning(f"Called activate_light_bar_%s service", mode.value)
        lbde = LightBarDisplayEffect(
            mode,
            **{
                k: v
                for k, v in call.data.items()
                if k not in (ATTR_AREA_ID, ATTR_DEVICE_ID, ATTR_ENTITY_ID, ATTR_DEVICES)
            },
        )
        devices: set[Doppler] = call.data[ATTR_DEVICES]
        await call_doppyler_api_across_devices(devices, "set_light_bar_effect", lbde)
