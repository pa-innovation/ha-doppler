"""Models for mini display number."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TypedDict

from ..const import ATTR_COLOR, ATTR_DURATION
from .color import Color


class MiniDisplayNumberDict(TypedDict):
    """minidisplaynumber dict"""

    num: int
    duration: int
    color: list[int]


@dataclass
class MiniDisplayNumber:
    """MiniDisplayNumber class."""

    number: int
    duration: timedelta
    color: Color

    def to_dict(self) -> MiniDisplayNumberDict:
        """Convert MiniDisplayNumber to MiniDisplayNumberDict."""
        return {
            "num": self.number,
            ATTR_DURATION: int(self.duration.total_seconds()),
            ATTR_COLOR: self.color.to_list(),
        }

    @staticmethod
    def from_dict(mdn_dict: MiniDisplayNumberDict) -> "MiniDisplayNumber":
        """Convert MiniDisplayNumberDict to MiniDisplayNumber."""
        return MiniDisplayNumber(
            mdn_dict["num"],
            timedelta(seconds=mdn_dict[ATTR_DURATION]),
            Color.from_list(mdn_dict[ATTR_COLOR]),
        )
