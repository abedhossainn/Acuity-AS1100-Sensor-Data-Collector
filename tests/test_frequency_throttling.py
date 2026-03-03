"""Tests for frequency/samples-per-second throttling."""

import unittest
import time
from datetime import datetime
from pathlib import Path

from app.domain.models import CollectionConfig, MeasurementMode, IntervalMode, Unit


class TestFrequencyThrottling(unittest.TestCase):
    """Test samples-per-second throttling functionality."""
    
    def test_throttling_calculation(self):
        """Test that the interval calculation is correct."""
        # 10 Hz = 1 sample every 0.1 seconds
        freq = 10.0
        interval = 1.0 / freq
        self.assertAlmostEqual(interval, 0.1, places=5)
        
        # 5 Hz = 1 sample every 0.2 seconds
        freq = 5.0
        interval = 1.0 / freq
        self.assertAlmostEqual(interval, 0.2, places=5)
        
        # 100 Hz = 1 sample every 0.01 seconds
        freq = 100.0
        interval = 1.0 / freq
        self.assertAlmostEqual(interval, 0.01, places=5)
    
    def test_throttling_simulation(self):
        """Simulate throttling logic to verify it works correctly."""
        # Simulate 10 Hz throttling
        target_hz = 10.0
        min_interval = 1.0 / target_hz
        
        samples_accepted = []
        samples_rejected = []
        next_sample_time = time.time()
        
        # Simulate incoming samples at ~20 Hz for 1 second
        start_time = time.time()
        sample_times = []
        elapsed = 0
        
        while elapsed < 1.0:
            now = time.time()
            elapsed = now - start_time
            
            # Simulate sample arrival
            if now >= next_sample_time:
                samples_accepted.append(now)
                next_sample_time = now + min_interval
            else:
                samples_rejected.append(now)
            
            # Simulate sensor sending at ~20 Hz
            time.sleep(0.05)
        
        # Should have ~10 samples accepted (10 Hz × 1 second)
        # Allow ±2 samples tolerance for timing variations
        self.assertGreaterEqual(len(samples_accepted), 8)
        self.assertLessEqual(len(samples_accepted), 12)
        
        # Verify spacing between accepted samples
        if len(samples_accepted) > 1:
            intervals = []
            for i in range(1, len(samples_accepted)):
                interval = samples_accepted[i] - samples_accepted[i-1]
                intervals.append(interval)
            
            avg_interval = sum(intervals) / len(intervals)
            # Should be close to 0.1 seconds (10 Hz)
            self.assertGreater(avg_interval, 0.08)
            self.assertLess(avg_interval, 0.12)
    
    def test_config_with_frequency_presets(self):
        """Test that config properly stores frequency values."""
        test_folder = Path.home() / "sensor_data"
        
        # Test 10 Hz
        config = CollectionConfig(
            port="COM4",
            sensor_id=0,
            mode=MeasurementMode.CONTINUOUS,
            interval_mode=IntervalMode.HOST_THROTTLED,
            interval_hz=10.0,
            unit=Unit.MM,
            output_folder=str(test_folder),
        )
        self.assertEqual(config.interval_hz, 10.0)
        
        # Test 100 Hz
        config = CollectionConfig(
            port="COM4",
            sensor_id=0,
            mode=MeasurementMode.CONTINUOUS,
            interval_mode=IntervalMode.HOST_THROTTLED,
            interval_hz=100.0,
            unit=Unit.MM,
            output_folder=str(test_folder),
        )
        self.assertEqual(config.interval_hz, 100.0)
        
        # Test 1 Hz
        config = CollectionConfig(
            port="COM4",
            sensor_id=0,
            mode=MeasurementMode.CONTINUOUS,
            interval_mode=IntervalMode.HOST_THROTTLED,
            interval_hz=1.0,
            unit=Unit.MM,
            output_folder=str(test_folder),
        )
        self.assertEqual(config.interval_hz, 1.0)


if __name__ == "__main__":
    unittest.main()
