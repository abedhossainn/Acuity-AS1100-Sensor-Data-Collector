"""Unit conversion utilities for AS1100 sensor data."""

from app.domain.models import Unit


# Conversion factors from millimeters to target units
CONVERSION_FACTORS = {
    Unit.MM: 1.0,
    Unit.CM: 0.1,
    Unit.M: 0.001,
    Unit.KM: 0.000001,
    Unit.FT: 0.00328084,
    Unit.IN: 0.0393701,
}


def convert_0p1mm_to_unit(value_0p1mm: int, target_unit: Unit) -> float:
    """
    Convert AS1100 raw value (0.1 mm units) to target unit.
    
    Parameters
    ----------
    value_0p1mm : int
        Raw sensor value in 0.1 mm units
    target_unit : Unit
        Target unit for conversion
    
    Returns
    -------
    float
        Converted value in target unit
    """
    # First convert 0.1mm units to mm
    value_mm = value_0p1mm * 0.1
    
    # Then convert mm to target unit
    factor = CONVERSION_FACTORS.get(target_unit, 1.0)
    return value_mm * factor


def format_converted_value(value: float, unit: Unit, precision: int = 4) -> str:
    """
    Format a converted value for display.
    
    Parameters
    ----------
    value : float
        The numeric value
    unit : Unit
        The unit
    precision : int
        Decimal places to display
    
    Returns
    -------
    str
        Formatted string (e.g., "271.8 mm")
    """
    return f"{value:.{precision}g} {unit.value}"


def get_unit_symbol(unit: Unit) -> str:
    """Get the symbol for a unit."""
    symbols = {
        Unit.MM: "mm",
        Unit.CM: "cm",
        Unit.M: "m",
        Unit.KM: "km",
        Unit.FT: "ft",
        Unit.IN: "in",
    }
    return symbols.get(unit, unit.value)
