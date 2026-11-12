"""Models for smart button."""

from dataclasses import dataclass
from typing import TypedDict

from .color import Color


class SmartButtonConfigurationDict(TypedDict):
    """Representation of a smart button configuration."""

    url: str
    data: str  # button number
    command: str
    color: list[int]  # 3 item list


@dataclass
class SmartButtonConfiguration:
    """Class to represent a smart button configuration."""

    webhook_url: str
    command: str
    color: Color

    def to_dict(self) -> SmartButtonConfigurationDict:
        """Convert SmartButtonConfiguration to SmartButtonConfigurationDict."""
        return {
            "url": self.webhook_url,
            "command": self.command,
            "color": self.color.to_list(),
        }

    @staticmethod
    def from_dict(
        sbc_dict: SmartButtonConfigurationDict,
    ) -> "SmartButtonConfiguration":
        """Convert SmartButtonConfigurationDict to SmartButtonConfiguration."""
        return SmartButtonConfiguration(
            sbc_dict["url"], sbc_dict["command"], Color.from_list(sbc_dict["color"])
        )
