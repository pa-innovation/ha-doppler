"""Models for main display text."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TypedDict

from ..const import ATTR_COLOR, ATTR_DURATION, ATTR_SPEED, ATTR_TEXT
from .color import Color


class MainDisplayTextDict(TypedDict):
    """maindisplaytext dict"""

    text: str
    duration: int
    speed: int
    color: list[int]


@dataclass
class MainDisplayText:
    """MainDisplayText class."""

    text: str
    duration: timedelta
    speed: int
    color: Color

    def to_dict(self) -> MainDisplayTextDict:
        """Convert MainDisplayText to MainDisplayTextDict."""
        return {
            ATTR_TEXT: self.text,
            ATTR_DURATION: int(self.duration.total_seconds()),
            ATTR_SPEED: self.speed,
            ATTR_COLOR: self.color.to_list(),
        }

    @staticmethod
    def from_dict(mdt_dict: MainDisplayTextDict) -> "MainDisplayText":
        """Convert MainDisplayTextDict to MainDisplayText."""
        return MainDisplayText(
            mdt_dict[ATTR_TEXT],
            timedelta(seconds=mdt_dict[ATTR_DURATION]),
            mdt_dict[ATTR_SPEED],
            Color.from_list(mdt_dict[ATTR_COLOR]),
        )
