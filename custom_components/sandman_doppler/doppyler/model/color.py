"""Models for color."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict


class ColorDict(TypedDict):
    """Representation of a color dictionary."""

    red: int
    green: int
    blue: int


@dataclass
class Color:
    """Color class."""

    red: int
    green: int
    blue: int

    def to_list(self) -> list[int]:
        """Convert Color to a list of ints."""
        return [self.red, self.green, self.blue]

    def to_dict(self) -> ColorDict:
        """Convert Color to a dictionary."""
        return ColorDict(red=self.red, green=self.green, blue=self.blue)

    @staticmethod
    def from_list(color_list: list[int]) -> "Color":
        """Convert a list to a Color."""
        if len(color_list) != 3 or any(not isinstance(x, int) for x in color_list):
            raise ValueError("Input must be a three integer list")
        if any(0 > x > 255 for x in color_list):
            raise ValueError("Each color value must be between 0 and 255")
        return Color(*color_list)

    @staticmethod
    def from_dict(color_dict: ColorDict) -> "Color":
        """Convert a dictionary to a Color."""
        for color in ("red", "green", "blue"):
            if color not in color_dict:
                raise ValueError(f"Dictionary is missing `{color}` color value")
        return Color(color_dict["red"], color_dict["green"], color_dict["blue"])
