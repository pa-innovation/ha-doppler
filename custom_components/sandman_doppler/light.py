"""Light platform for Doppler Sandman."""
from __future__ import annotations

from dataclasses import dataclass
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
)
from doppyler.model.color import Color
from doppyler.model.doppler import Doppler
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    COLOR_MODE_RGB,
    LightEntity,
    LightEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DopplerDataUpdateCoordinator
from .const import DOMAIN
from .entity import DopplerEntity

_LOGGER = logging.getLogger(__name__)


@dataclass
class DopplerLightEntityDescription(LightEntityDescription):
    """Class to describe Doppler light entities."""

    color_attr: str | None = None
    brightness_attr: str | None = None
    day_or_night: Literal["day", "night"] | None = None
    display_or_button: Literal["display", "button"] | None = None


ENTITY_DESCRIPTIONS = [
    DopplerLightEntityDescription(
        "Day Display",
        icon="mdi:clock-digital",
        name="Day Display",
        color_attr=ATTR_DAY_DISPLAY_COLOR,
        brightness_attr=ATTR_DAY_DISPLAY_BRIGHTNESS,
        day_or_night="day",
        display_or_button="display",
    ),
    DopplerLightEntityDescription(
        "Night Display",
        icon="mdi:clock-digital",
        name="Night Display",
        color_attr=ATTR_NIGHT_DISPLAY_COLOR,
        brightness_attr=ATTR_NIGHT_DISPLAY_BRIGHTNESS,
        day_or_night="night",
        display_or_button="display",
    ),
    DopplerLightEntityDescription(
        "Day Button",
        icon="mdi:gesture-tap-button",
        name="Day Button",
        color_attr=ATTR_DAY_BUTTON_COLOR,
        brightness_attr=ATTR_DAY_BUTTON_BRIGHTNESS,
        day_or_night="day",
        display_or_button="button",
    ),
    DopplerLightEntityDescription(
        "Night Button",
        icon="mdi:gesture-tap-button",
        name="Night Button",
        color_attr=ATTR_NIGHT_BUTTON_COLOR,
        brightness_attr=ATTR_NIGHT_BUTTON_BRIGHTNESS,
        day_or_night="night",
        display_or_button="button",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
) -> None:
    """Setup sensor platform."""
    coordinator: DopplerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for device in coordinator.api.devices.values():
        entities.extend(
            [
                BaseDopplerLight(coordinator, entry, device, description)
                for description in ENTITY_DESCRIPTIONS
            ]
        )
    async_add_devices(entities)


class BaseDopplerLight(DopplerEntity, LightEntity):
    """Base Doppler Light class."""

    _attr_color_mode = COLOR_MODE_RGB
    _attr_supported_color_modes = {COLOR_MODE_RGB}
    _attr_is_on = True

    def __init__(
        self,
        coordinator: DopplerDataUpdateCoordinator,
        entry: ConfigEntry,
        device: Doppler,
        description: DopplerLightEntityDescription,
    ) -> None:
        """Initialize the light."""
        super().__init__(coordinator, entry, device, description.name)
        self.entity_description: DopplerLightEntityDescription = description
        self._color_attr = description.color_attr
        self._brightness_attr = description.brightness_attr
        self._day_or_night = description.day_or_night
        self._display_or_button = description.display_or_button

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the rgb color value [int, int, int]."""
        color: Color | None = self.device_data[self._color_attr]
        if not color:
            return None
        return (color.red, color.green, color.blue)

    @property
    def brightness(self) -> int:
        """Return the brightness of this light between 0..255."""
        brightness = self.device_data[self._brightness_attr]
        if brightness is not None:
            return brightness * 255 // 100
        return 0

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the device on."""
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        rgb_color = kwargs.get(ATTR_RGB_COLOR)
        base_func_name = f"set_{self._day_or_night}_{self._display_or_button}"
        if brightness is not None:
            brightness_func_name = f"{base_func_name}_brightness"
            self.device_data[self._brightness_attr] = await getattr(
                self.device, brightness_func_name
            )(self.device, brightness * 100 // 255)
        if rgb_color is not None:
            color_func_name = f"{base_func_name}_color"
            self.device_data[self._color_attr] = await getattr(
                self.device, color_func_name
            )(self.device, Color(rgb_color[0], rgb_color[1], rgb_color[2]))

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        _LOGGER.warning(
            "Turning off the Doppler %s %s is not supported.",
            self._display_or_button,
            "light" if self._display_or_button == "display" else "lights",
        )
