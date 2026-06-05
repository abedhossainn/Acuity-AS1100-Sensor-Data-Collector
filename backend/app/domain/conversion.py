"""Unit conversion utilities for AS1100 sensor data."""

from enum import Enum


# Conversion factors from millimeters to target units
CONVERSION_FACTORS = {
    "millimeters": 1.0,
    "centimeters": 0.1,
    "meters": 0.001,
    "kilometers": 0.000001,
    "feet": 0.00328084,
    "inches": 0.0393701,
}


def convert_0p1mm_to_unit(value_0p1mm: int, target_unit) -> float:
    """
    Convert AS1100 raw value (0.1 mm units) to target unit.
    
    Parameters
    ----------
    value_0p1mm : int
        Raw sensor value in 0.1 mm units
    target_unit : Unit or UnitEnum or str
        Target unit for conversion (can be Enum or string value)
    
    Returns
    -------
    float
        Converted value in target unit
    """
    # Get the unit string (handles Enum or direct string)
    if isinstance(target_unit, Enum):
        unit_str = target_unit.value
    else:
        unit_str = str(target_unit)
    
    # First convert 0.1mm units to mm
    value_mm = value_0p1mm * 0.1
    
    # Then convert mm to target unit
    factor = CONVERSION_FACTORS.get(unit_str, 1.0)
    return value_mm * factor

