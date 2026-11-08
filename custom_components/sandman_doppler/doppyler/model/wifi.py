"""Model for WiFi data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TypedDict


class WifiStatusDict(TypedDict):
    """Dictionary for wifi status response."""

    uptime: int
    ssid: str
    str: int


@dataclass
class WifiStatus:
    """Wifi Status class."""

    uptime: timedelta
    ssid: str
    signal_strength: str

    def to_dict(self) -> WifiStatusDict:
        """Convert WifiStatus to WifiStatusDict."""
        return {
            "uptime": int(self.uptime.total_seconds() * 1000),
            "ssid": self.ssid,
            "str": self.signal_strength,
        }

    @staticmethod
    def from_dict(wifi_status: WifiStatusDict) -> None:
        """Convert WifiStatusDict to WifiStatus."""
        return WifiStatus(
            timedelta(milliseconds=wifi_status["uptime"]),
            wifi_status["ssid"],
            wifi_status["str"],
        )
