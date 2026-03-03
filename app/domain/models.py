"""Core domain models for AS1100 sensor data collection."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class MeasurementMode(Enum):
    """Measurement mode selection."""
    CONTINUOUS = "continuous"
    SINGLE = "single"


class IntervalMode(Enum):
    """How intervals are controlled."""
    SENSOR_TIMED = "sensor_timed"  # Use AS1100 s#h+ms command
    HOST_THROTTLED = "host_throttled"  # Max speed, throttle in app


class Unit(Enum):
    """Distance units for output conversion."""
    MM = "millimeters"
    CM = "centimeters"
    M = "meters"
    KM = "kilometers"
    FT = "feet"
    IN = "inches"


@dataclass
class SampleRecord:
    """Single measurement record with timestamp and metadata."""
    timestamp_iso: str  # ISO 8601 format
    epoch_ms: int  # Milliseconds since epoch
    raw_0p1mm: int  # Raw sensor value (0.1 mm units)
    value: float  # Converted to selected unit
    unit: str  # Unit name
    mode: str  # "continuous" or "single"
    interval_hz: Optional[float]  # Samples per second (if applicable)
    sensor_id: int  # AS1100 sensor ID
    response: str  # Raw response from sensor


@dataclass
class CollectionConfig:
    """Configuration for a data collection session."""
    port: str  # Serial port (e.g., "COM4")
    sensor_id: int  # AS1100 sensor ID (default 0)
    mode: MeasurementMode  # continuous or single
    interval_mode: IntervalMode  # sensor-timed or host-throttled
    interval_hz: float  # Desired samples per second
    unit: Unit  # Output unit conversion
    output_folder: str  # Path to save CSV
    baudrate: int = 19200
    timeout: float = 2.0


@dataclass
class SensorInfo:
    """Cached sensor information."""
    serial_number: str
    firmware_version: str
    measure_fw: str
    interface_fw: str
