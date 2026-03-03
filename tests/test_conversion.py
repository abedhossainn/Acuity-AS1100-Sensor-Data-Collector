"""Tests for unit conversion."""

import unittest

from app.domain.models import Unit
from app.domain.conversion import convert_0p1mm_to_unit, format_converted_value


class TestConversion(unittest.TestCase):
    """Test conversion functions."""
    
    def test_convert_to_mm(self):
        """Test conversion to millimeters."""
        # 2718 * 0.1 mm = 271.8 mm
        value = convert_0p1mm_to_unit(2718, Unit.MM)
        self.assertAlmostEqual(value, 271.8, places=1)
    
    def test_convert_to_cm(self):
        """Test conversion to centimeters."""
        # 2718 * 0.1 mm = 27.18 cm
        value = convert_0p1mm_to_unit(2718, Unit.CM)
        self.assertAlmostEqual(value, 27.18, places=2)
    
    def test_convert_to_meters(self):
        """Test conversion to meters."""
        # 2718 * 0.1 mm = 0.2718 m
        value = convert_0p1mm_to_unit(2718, Unit.M)
        self.assertAlmostEqual(value, 0.2718, places=4)
    
    def test_convert_to_feet(self):
        """Test conversion to feet."""
        # 1000 * 0.1 mm = 100 mm = 0.328084 ft (approximately)
        value = convert_0p1mm_to_unit(1000, Unit.FT)
        self.assertAlmostEqual(value, 0.328084, places=5)
    
    def test_convert_to_km(self):
        """Test conversion to kilometers."""
        # 10,000,000 * 0.1 mm = 1 km
        value = convert_0p1mm_to_unit(10000000, Unit.KM)
        self.assertAlmostEqual(value, 1.0, places=6)
    
    def test_format_converted_value(self):
        """Test formatted output."""
        formatted = format_converted_value(271.8, Unit.MM, precision=3)
        # g format rounds 271.8 to 272 with precision=3
        self.assertIn("millimeters", formatted)
        self.assertIsInstance(formatted, str)
        self.assertGreater(len(formatted), 0)


if __name__ == "__main__":
    unittest.main()
