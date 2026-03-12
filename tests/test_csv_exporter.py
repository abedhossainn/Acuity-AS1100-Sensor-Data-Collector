"""Tests for CSV export."""

import unittest
import tempfile
from pathlib import Path

from app.domain.models import SampleRecord
from app.io.csv_exporter import CSVExporter


class TestCSVExporter(unittest.TestCase):
    """Test CSV export functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_folder = self.temp_dir.name
    
    def tearDown(self):
        """Clean up."""
        self.temp_dir.cleanup()
    
    def test_csv_creation(self):
        """Test CSV file creation."""
        with CSVExporter(self.output_folder, "test_session") as exporter:
            self.assertTrue(exporter.get_filepath().exists())
    
    def test_write_sample(self):
        """Test writing a sample."""
        sample = SampleRecord(
            timestamp_iso="2026-03-03T12:00:00",
            epoch_ms=1740991200000,
            raw_0p1mm=2718,
            value=271.8,
            unit="millimeters",
            mode="continuous",
            interval_hz=10.0,
            sensor_id=0,
            response="g0g+00002718",
        )
        
        with CSVExporter(self.output_folder, "test_session") as exporter:
            exporter.write_sample(sample)
            filepath = exporter.get_filepath()
        
        # Verify file contents
        with open(filepath, "r") as f:
            lines = f.readlines()
            self.assertGreaterEqual(len(lines), 2)  # Header + at least one row
            self.assertIn("timestamp", lines[0])
            self.assertIn("distance", lines[0])
            self.assertIn("mode", lines[0])
            self.assertIn("2026-03-03T12:00:00", lines[1])

    def test_decimal_places_formatting(self):
        """Test decimal places formatting in CSV output."""
        sample = SampleRecord(
            timestamp_iso="2026-03-03T12:00:00",
            epoch_ms=1740991200000,
            raw_0p1mm=12345,
            value=1234.56789,
            unit="millimeters",
            mode="continuous",
            interval_hz=10.0,
            sensor_id=0,
            response="g0h+00012345",
        )
        
        # Test with 2 decimal places
        with CSVExporter(self.output_folder, "test_2dp", decimal_places=2) as exporter:
            exporter.write_sample(sample)
            filepath = exporter.get_filepath()
        
        with open(filepath, "r") as f:
            lines = f.readlines()
            self.assertIn("1234.57", lines[1])  # Rounded to 2 decimal places
        
        # Test with 6 decimal places
        with CSVExporter(self.output_folder, "test_6dp", decimal_places=6) as exporter:
            exporter.write_sample(sample)
            filepath = exporter.get_filepath()
        
        with open(filepath, "r") as f:
            lines = f.readlines()
            self.assertIn("1234.567890", lines[1])  # Formatted to 6 decimal places


if __name__ == "__main__":
    unittest.main()

