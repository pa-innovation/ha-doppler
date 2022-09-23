"""Helpers for Sandman Doppler Clocks."""
from enum import Enum


def normalize_enum_name(enum_val: Enum) -> str:
    """Normalize an enum's name to a string."""
    return enum_val.name.replace("_", " ").title()


def get_enum_from_name(enum: Enum, name: str) -> Enum:
    """Get an enum value from a name."""
    return enum[name.replace(" ", "_").upper()]
