"""Tests for sensor response parsing."""

import unittest

from app.sensor.parsing import (
    parse_distance_response,
    parse_signal_strength_response,
    parse_temperature_response,
    parse_firmware_version,
    parse_serial_number,
    parse_error_stack,
    is_error_response,
    parse_error_code,
)


class TestParsing(unittest.TestCase):
    """Test parsing functions."""
    
    def test_parse_distance_response(self):
        """Test distance response parsing."""
        response = "g0g+00002718"
        value = parse_distance_response(response)
        self.assertEqual(value, 2718)
    
    def test_parse_distance_response_invalid(self):
        """Test distance response parsing with invalid input."""
        self.assertIsNone(parse_distance_response("invalid"))
        self.assertIsNone(parse_distance_response(None))
        self.assertIsNone(parse_distance_response(""))
    
    def test_parse_signal_strength(self):
        """Test signal strength parsing."""
        response = "g0m+00004115"
        value = parse_signal_strength_response(response)
        self.assertEqual(value, 4115)
    
    def test_parse_temperature(self):
        """Test temperature parsing."""
        response = "g0t+00000228"
        value = parse_temperature_response(response)
        self.assertAlmostEqual(value, 22.8, places=1)
    
    def test_parse_firmware_version(self):
        """Test firmware version parsing."""
        response = "g0sv+00430121"
        measure_fw, iface_fw = parse_firmware_version(response)
        self.assertEqual(measure_fw, "0043")
        self.assertEqual(iface_fw, "0121")
    
    def test_parse_serial_number(self):
        """Test serial number parsing."""
        response = "g0sn+40250215"
        sn = parse_serial_number(response)
        self.assertEqual(sn, "40250215")
    
    def test_parse_error_stack(self):
        """Test error stack parsing."""
        response = "g0re+200+211+255"
        codes = parse_error_stack(response)
        self.assertEqual(codes, [200, 211, 255])
    
    def test_is_error_response(self):
        """Test error response detection."""
        self.assertTrue(is_error_response("g0@E203"))
        self.assertFalse(is_error_response("g0g+00002718"))
        self.assertFalse(is_error_response(""))
    
    def test_parse_error_code(self):
        """Test error code parsing."""
        code = parse_error_code("g0@E203")
        self.assertEqual(code, 203)


if __name__ == "__main__":
    unittest.main()
