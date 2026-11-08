"""Models for setting light bar effects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from typing import Any, TypedDict

from ..const import (
    ATTR_COLORS,
    ATTR_DIRECTION,
    ATTR_DURATION,
    ATTR_GAP,
    ATTR_RAINBOW,
    ATTR_SIZE,
    ATTR_SPARKLE,
    ATTR_SPEED,
)
from .color import Color


class Sparkle(Enum):
    """Enum to represent sparkle."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    DEFAULT = NONE


class Direction(Enum):
    """Enum to represent direction."""

    BOUNCE = "bounce"
    LEFT = "left"
    RIGHT = "right"
    DEFAULT = RIGHT


class Mode(Enum):
    """Enum to represent direction."""

    SET = "set"
    SET_EACH = "set-each"
    BLINK = "blink"
    PULSE = "pulse"
    COMET = "comet"
    SWEEP = "sweep"


class LightBarDisplayEffectDict(TypedDict):
    """lightBarDisplayEffect dict."""

    colors: list[list[int]]
    duration: int
    speed: int
    attributes: dict[str, Any]


def _convert_dict_val_to_colors(
    colors_list: list[list[int]] | None,
) -> list[Color] | None:
    """Convert dictionary value to colors."""
    if not colors_list:
        return None
    return [Color.from_list(color_list) for color_list in colors_list]


def _convert_dict_val_to_enum(enum: Enum, val: str | None) -> str | None:
    """Convert dictionary value to enum."""
    if val is None:
        return None
    return enum(val)


def _convert_str_dict_val_to_int(val: str | None) -> str | None:
    """Convert string dictionary value to int."""
    if val is None:
        return None
    return int(val)


def _convert_str_dict_val_to_bool(val: str | None) -> str | None:
    """Convert string dictionary value to bool."""
    if val is None:
        return None
    return val.lower() == "true"


@dataclass
class LightBarDisplayEffect:
    """LightBarDisplayEffect class."""

    mode: Mode
    duration: timedelta
    colors: list[Color] | None = None
    speed: int | None = None
    sparkle: Sparkle | None = None
    rainbow: bool | None = None
    size: int | None = None
    direction: Direction | None = None
    gap: int | None = None

    def _convert_colors_to_dict_val(self) -> list[list[int]] | None:
        """Convert colors to proper dictionary value."""
        if not self.colors:
            return None
        return [color.to_list() for color in self.colors]

    def _convert_enum_to_dict_val(self, attr_name: str) -> str | None:
        """Convert enum to proper dictionary value."""
        attr: Enum | None = getattr(self, attr_name)
        if attr is None:
            return None
        return attr.value

    def _convert_int_or_bool_to_str_dict_val(
        self, attr_name: str, lower: bool = False
    ) -> str | None:
        """Convert int to proper dictionary value when it should be passed as str."""
        attr: int | bool | None = getattr(self, attr_name)
        if attr is None:
            return None
        if lower:
            return str(attr).lower()
        return str(attr)

    def to_dict(self) -> LightBarDisplayEffectDict:
        """Convert LightbarDisplayEffect to LightbarDisplayEffectDict."""
        return {
            k: v
            for k, v in {
                ATTR_COLORS: self._convert_colors_to_dict_val(),
                ATTR_DURATION: int(self.duration.total_seconds()),
                ATTR_SPEED: self.speed,
                "attributes": {
                    k1: v1
                    for k1, v1 in {
                        "display": self.mode.value,
                        ATTR_SPARKLE: self._convert_enum_to_dict_val("sparkle"),
                        ATTR_RAINBOW: self._convert_int_or_bool_to_str_dict_val(
                            ATTR_RAINBOW, True
                        ),
                        ATTR_SIZE: self._convert_int_or_bool_to_str_dict_val("size"),
                        ATTR_DIRECTION: self._convert_enum_to_dict_val("direction"),
                        ATTR_GAP: self._convert_int_or_bool_to_str_dict_val("gap"),
                    }.items()
                    if v1 is not None
                },
            }.items()
            if v is not None
        }

    @staticmethod
    def from_dict(lbd_dict: LightBarDisplayEffectDict) -> "LightBarDisplayEffect":
        """Convert LightbarDisplayDict to LightbarDisplayEffect."""
        attributes = lbd_dict["attributes"]
        return LightBarDisplayEffect(
            Mode(attributes["display"]),
            timedelta(seconds=lbd_dict[ATTR_DURATION]),
            colors=_convert_dict_val_to_colors(lbd_dict.get(ATTR_COLORS)),
            speed=lbd_dict.get(ATTR_SPEED),
            sparkle=_convert_dict_val_to_enum(Sparkle, attributes.get(ATTR_SPARKLE)),
            rainbow=_convert_str_dict_val_to_bool(attributes.get(ATTR_RAINBOW)),
            size=_convert_str_dict_val_to_int(attributes.get(ATTR_SIZE)),
            direction=_convert_dict_val_to_enum(
                Direction, attributes.get(ATTR_DIRECTION)
            ),
            gap=_convert_str_dict_val_to_int(attributes.get(ATTR_GAP)),
        )
