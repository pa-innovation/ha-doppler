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
    mode: RainbowMode


@dataclass
class RainbowConfiguration:
    """Rainbow class."""

    speed: int
    mode: RainbowMode

    def to_dict(self) -> RainbowDict:
        return RainbowDict(speed=self.speed, mode=self.mode)

    @staticmethod
    def from_dict(rainbow_dict: RainbowDict) -> RainbowConfiguration:
        if "speed" not in rainbow_dict:
            raise ValueError("Dictionary is missing speed value")
        if "mode" not in rainbow_dict:
            raise ValueError("Dictionary is missing mode value")
        return RainbowConfiguration(rainbow_dict["speed"], rainbow_dict["mode"])
