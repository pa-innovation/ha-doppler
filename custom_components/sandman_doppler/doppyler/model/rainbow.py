from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import TypedDict

_LOGGER = logging.getLogger(__name__)


class RainbowMode(str, Enum):
    """Whether Rainbow is set for day, night, of both"""

    DAY = "day"
    NIGHT = "night"
    BOTH = "both"


class RainbowDict(TypedDict):
    """Representation of rainbow mode"""

    speed: int
    mode: RainbowMode | str


@dataclass
class RainbowConfiguration:
    """Rainbow class."""

    speed: int
    mode: RainbowMode | str

    def to_dict(self) -> RainbowDict:
        return RainbowDict(speed=self.speed, mode=self.mode)

    @staticmethod
    def from_dict(rainbow_dict: RainbowDict) -> RainbowConfiguration:
        if "speed" not in rainbow_dict:
            raise ValueError("Dictionary is missing speed value")
        if "mode" not in rainbow_dict:
            raise ValueError("Dictionary is missing mode value")
        mode = rainbow_dict["mode"]
        try:
            mode = RainbowMode(mode)
        except ValueError:
            # Keep a value this library doesn't know, so it is sent back unchanged.
            _LOGGER.debug("Unknown rainbow mode from the clock: %s", mode)
        return RainbowConfiguration(int(rainbow_dict["speed"]), mode)
