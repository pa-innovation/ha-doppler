"""Model for weather."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import TypedDict


class WeatherMode(IntEnum):
    """Weather mode."""

    OFF = 0  # Weather Service Off
    FAHRENHEIT_SCALE = 1  # Daily high weatherapi.com
    CELSIUS_SCALE = 2  # Daily high
    HUMIDITY_SCALE = 3  # Daily avg humidity
    AQI_SCALE = 4  # Daily AQI AM
    FAHRENHEIT_SCALE_MIN = 5  # Min daily temp
    CELSIUS_SCALE_MIN = 6  # Min daily temp
    HUMIDITY_SCALE_MIN = 7  # Min daily humidity
    HUMIDITY_SCALE_MAX = 8  # Max daily humidity
    FAHRENHEIT_SCALE_HOURLY = 9  # Hourly temp
    CELSIUS_SCALE_HOURLY = 10  # Hourly temp
    HUMIDITY_SCALE_HOURLY = 11  # Hourly humidity
    AQI_SCALE_HOURLY = 12  # Hourly AQI
    NWS_DAILY_FORECAST_FAHRENHEIT_SCALE = 13  # US NWS api
    NWS_DAILY_FORECAST_CELCIUS_SCALE = 14
    NWS_HOURLY_OBSERVATION_FAHRENHEIT_SCALE = 15
    NWS_HOURLY_OBSERVATION_CELCIUS_SCALE = 16
    NWS_HOURLY_OBSERVATION_HUMIDITY_SCALE = 17


class WeatherConfigurationDict(TypedDict):
    """Weather configuration dictionary response from API."""

    wsonoff: bool
    location: str
    wsmode: int


@dataclass
class WeatherConfiguration:
    """Weather Configuration class."""

    enabled: bool
    location: str
    mode: WeatherMode

    def to_dict(self) -> WeatherConfigurationDict:
        """Convert to dict."""
        return {
            "wsonoff": self.enabled,
            "location": self.location,
            "wsmode": self.mode.value,
        }

    @staticmethod
    def from_dict(weather_dict: WeatherConfigurationDict) -> "WeatherConfiguration":
        """Create WeatherConfiguration from dict."""
        return WeatherConfiguration(
            weather_dict["wsonoff"],
            weather_dict["location"],
            WeatherMode(weather_dict["wsmode"]),
        )
