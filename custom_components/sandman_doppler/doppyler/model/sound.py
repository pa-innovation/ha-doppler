"""Models for audio."""

from __future__ import annotations

from enum import Enum


class SoundPreset(Enum):
    """Sound Preset Enum."""

    BALANCED = "PRESET1"
    BASS_BOOST = "PRESET2"
    HIGH_BOOST = "PRESET3"
    MID_BOOST = "PRESET4"
    UNTUNED = "PRESET5"
