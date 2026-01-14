"""Light platform for Doppler Sandman."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
import functools
import logging
from typing import Any, Literal

from doppyler.const import (
    ATTR_DAY_BUTTON_BRIGHTNESS,
    ATTR_DAY_BUTTON_COLOR,
    ATTR_DAY_DISPLAY_BRIGHTNESS,
    ATTR_DAY_DISPLAY_COLOR,
    ATTR_NIGHT_BUTTON_BRIGHTNESS,
    ATTR_NIGHT_BUTTON_COLOR,
    ATTR_NIGHT_DISPLAY_BRIGHTNESS,
    ATTR_NIGHT_DISPLAY_COLOR,
    ATTR_SMART_BUTTON_COLOR,
)
from doppyler.model.color import Color
from doppyler.model.doppler import Doppler
from doppyler.model.smart_button import SmartButtonConfiguration

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
    LightEntityDescription,
)
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from . import DopplerDataUpdateCoordinator
from .const import DOMAIN
from .entity import DopplerEntity

_LOGGER = logging.getLogger(__name__)


@dataclass
class DopplerLightEntityDescription(LightEntityDescription):
    """Class to describe Doppler light entities."""

    color_key: str | None = None
    set_color_func: Callable[[Doppler, Color], Coroutine[Any, Any, Any]] | None = None
    brightness_key: str | None = None
    set_brightness_func: Callable[[Doppler, int], Coroutine[Any, Any, int]] | None = (
        None
    )


LIGHT_ENTITY_DESCRIPTIONS = [
    DopplerLightEntityDescription(
        "Day Display",
        icon="mdi:clock-digital",
        name="Day Display",
        color_key=ATTR_DAY_DISPLAY_COLOR,
        set_color_func=lambda dev, color: dev.set_day_display_color(color),
        brightness_key=ATTR_DAY_DISPLAY_BRIGHTNESS,
        set_brightness_func=lambda dev, brightness: dev.set_day_display_brightness(
            brightness
        ),
    ),
    DopplerLightEntityDescription(
        "Night Display",
        icon="mdi:clock-digital",
        name="Night Display",
        color_key=ATTR_NIGHT_DISPLAY_COLOR,
        set_color_func=lambda dev, color: dev.set_night_display_color(color),
        brightness_key=ATTR_NIGHT_DISPLAY_BRIGHTNESS,
        set_brightness_func=lambda dev, brightness: dev.set_night_display_brightness(
            brightness
        ),
    ),
    DopplerLightEntityDescription(
        "Day Button",
        icon="mdi:gesture-tap-button",
        name="Day Button",
        color_key=ATTR_DAY_BUTTON_COLOR,
        set_color_func=lambda dev, color: dev.set_day_button_color(color),
        brightness_key=ATTR_DAY_BUTTON_BRIGHTNESS,
        set_brightness_func=lambda dev, brightness: dev.set_day_button_brightness(
            brightness
        ),
    ),
    DopplerLightEntityDescription(
        "Night Button",
        icon="mdi:gesture-tap-button",
        name="Night Button",
        color_key=ATTR_NIGHT_BUTTON_COLOR,
        set_color_func=lambda dev, color: dev.set_night_button_color(color),
        brightness_key=ATTR_NIGHT_BUTTON_BRIGHTNESS,
        set_brightness_func=lambda dev, brightness: dev.set_night_button_brightness(
            brightness
        ),
    ),
]


def set_smart_button_color_func(
    i: int,
) -> Callable[[Doppler, Color], Coroutine[Any, Any, SmartButtonConfiguration]]:
    """Return a coroutine to set the smart button color."""
    return lambda dev, color: dev.set_smart_button_configuration(i, color=color)


SMART_BUTTON_LIGHT_ENTITY_DESCRIPTIONS = [
    DopplerLightEntityDescription(
        f"Smart Button {i}",
        icon="mdi:gesture-tap-button",
        name=f"Smart Button {i}",
        color_key=f"{ATTR_SMART_BUTTON_COLOR}_{i}",
        set_color_func=set_smart_button_color_func(i),
    )
    for i in range(1, 3)
]


def get_split_key(entity_description: DopplerLightEntityDescription) -> tuple[str, str]:
    """Split entity description keys into day/night and button/display."""
    split = entity_description.key.split(" ")
    return (split[0].lower(), split[1].lower())


def get_sync_light_types(
    entity_description: DopplerLightEntityDescription,
) -> tuple[str, str]:
    """Get the light types to sync with for this entity."""
    day_or_night, button_or_display = get_split_key(entity_description)
    split = entity_description.key.split(" ")
    return (
        f"{get_opposite_day_or_night(split[0].lower())}_{button_or_display}",
        f"{day_or_night}_{get_opposite_button_or_display(split[1].lower())}",
    )


def get_opposite_day_or_night(
    day_or_night: Literal["day", "night"],
) -> Literal["day", "night"]:
    """Return the opposite day or night."""
    return "day" if day_or_night == "night" else "night"


def get_opposite_button_or_display(
    button_or_display: Literal["button", "display"],
) -> Literal["button", "display"]:
    """Return the opposite button or display."""
    return "button" if button_or_display == "display" else "display"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
) -> None:
    """Setup light platform."""

    @callback
    def async_add_device(device: Doppler) -> None:
        """Add Doppler light entities."""
        coordinator: DopplerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
            device.dsn
        ]
        entities = [
            DopplerLight(coordinator, entry, device, description)
            for description in LIGHT_ENTITY_DESCRIPTIONS
        ]
        entities.extend(
            [
                DopplerSmartButtonLight(coordinator, entry, device, description)
                for description in SMART_BUTTON_LIGHT_ENTITY_DESCRIPTIONS
            ]
        )
        async_add_devices(entities)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, f"{DOMAIN}_{entry.entry_id}_device_added", async_add_device
        )
    )


class BaseDopplerLight(DopplerEntity[DopplerLightEntityDescription], LightEntity):
    """Base Doppler Light class."""

    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_is_on = True

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the rgb color value [int, int, int]."""
        if self.ed.color_key is None:
            return None
        color: Color | None = self.device_data.get(self.ed.color_key)
        if not color:
            return None
        return (color.red, color.green, color.blue)

    async def _async_set_brightness(self, brightness: int) -> int:
        """Set brightness on device."""
        brightness *= 100
        brightness //= 255
        brightness = self.device_data[self.ed.brightness_key] = (
            await self.ed.set_brightness_func(self.device, brightness)
        )
        return brightness

    async def _async_set_rgb_color(self, rgb_color: list[int]) -> Color:
        """Set color on device."""
        color = Color(rgb_color[0], rgb_color[1], rgb_color[2])
        await self.ed.set_color_func(self.device, color)
        self.device_data[self.ed.color_key] = color
        return color

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        _LOGGER.warning(
            "Turning off the Doppler %s light is not supported.", self.ed.key
        )


class DopplerLight(BaseDopplerLight):
    """Doppler Light class."""

    def __init__(
        self,
        coordinator: DopplerDataUpdateCoordinator,
        config_entry: ConfigEntry,
        device: Doppler,
        description: DopplerLightEntityDescription,
    ):
        """Initialize the Doppler Light."""
        super().__init__(coordinator, config_entry, device, description)
        self._ent_reg: er.EntityRegistry | None = None
        self._sync_signal_prefix = (
            f"{DOMAIN}_{self.config_entry.entry_id}_{self.device.dsn}_sync_from"
        )
        self._sync_unique_id_prefix = (
            f"{self.config_entry.unique_id}_{self.device.dsn}_sync"
        )

    @property
    def brightness(self) -> int:
        """Return the brightness of this light between 0..255."""
        if self.ed.brightness_key is None:
            return 0
        brightness = self.device_data.get(self.ed.brightness_key)
        if brightness is not None:
            return brightness * 255 // 100
        return 0

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the device on."""
        if (brightness := kwargs.get(ATTR_BRIGHTNESS)) is not None:
            brightness = await self._async_set_brightness(brightness)
            signal_name = (
                f"{self._sync_signal_prefix}_{slugify(self.ed.key)}_brightness"
            )
            _LOGGER.debug("%s sending signal %s", self.entity_id, signal_name)
            async_dispatcher_send(self.hass, signal_name, self.entity_id, brightness)
        if (rgb_color := kwargs.get(ATTR_RGB_COLOR)) is not None:
            color = await self._async_set_rgb_color(rgb_color)
            signal_name = f"{self._sync_signal_prefix}_{slugify(self.ed.key)}_color"
            _LOGGER.debug("%s sending signal %s", self.entity_id, signal_name)
            async_dispatcher_send(self.hass, signal_name, self.entity_id, color)
        if brightness is not None or rgb_color is not None:
            self.async_write_ha_state()

    @callback
    def async_sync_from_other_entity(
        self,
        switch_type: str,
        light_property: str,
        src_entity_id: str,
        val: int | Color,
    ) -> None:
        """Sync this entity from another entity."""
        unique_id = slugify(
            f"{self._sync_unique_id_prefix}_{switch_type}_{light_property}"
        )
        if not (
            sync_entity_id := self._ent_reg.async_get_entity_id(
                SWITCH_DOMAIN, DOMAIN, unique_id
            )
        ):
            _LOGGER.debug(
                (
                    "No sync required for %s %s from %s %s because sync entity with "
                    "unique ID %s does not exist"
                ),
                self.entity_id,
                light_property,
                src_entity_id,
                light_property,
                unique_id,
            )
            return

        if not (
            (state := self.hass.states.get(sync_entity_id)) and state.state == STATE_ON
        ):
            _LOGGER.debug(
                (
                    "No sync required for %s %s from %s %s because sync entity %s is "
                    "not on"
                ),
                self.entity_id,
                light_property,
                src_entity_id,
                light_property,
                sync_entity_id,
            )
            return

        _LOGGER.debug(
            "Syncing %s %s from %s %s (%s) because sync entity %s is on",
            self.entity_id,
            light_property,
            src_entity_id,
            light_property,
            val,
            sync_entity_id,
        )
        self.device_data[getattr(self.ed, f"{light_property}_key")] = val
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()

        self._ent_reg = er.async_get(self.hass)
        for light_property in ("color", "brightness"):
            for light_type, switch_type in zip(
                get_sync_light_types(self.ed), ("day_night", "button_display")
            ):
                signal_name = (
                    f"{self._sync_signal_prefix}_{light_type}_{light_property}"
                )
                listener_callback: Callable[[Color | int], None] = functools.partial(
                    self.async_sync_from_other_entity, switch_type, light_property
                )
                self.async_on_remove(
                    async_dispatcher_connect(self.hass, signal_name, listener_callback)
                )


class DopplerSmartButtonLight(BaseDopplerLight):
    """Doppler Smart Button Light class."""

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the device on."""
        if (rgb_color := kwargs.get(ATTR_RGB_COLOR)) is not None:
            await self._async_set_rgb_color(rgb_color)
            self.async_write_ha_state()
