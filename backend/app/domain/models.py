"""Core domain models for AS1100 sensor data collection."""

from enum import Enum


class Unit(Enum):
    """Distance units for output conversion."""
    MM = "millimeters"
    CM = "centimeters"
    M = "meters"
    KM = "kilometers"
    FT = "feet"
    IN = "inches"
