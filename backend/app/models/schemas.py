"""Pydantic models for API requests/responses."""

from typing import List, Optional
from pydantic import BaseModel, Field, model_validator
from enum import Enum

from app.domain.capabilities import get_effective_max_hz


class MeasurementModeEnum(str, Enum):
    """Measurement modes."""
    CONTINUOUS = "continuous"


class MeasuringModeEnum(str, Enum):
    """AS1100 measuring mode options (s#mc)."""
    NORMAL = "normal"
    FAST = "fast"
    PRECISE = "precise"
    TIMED = "timed"
    MOVING_TARGET = "moving_target"


class SerialProfileEnum(str, Enum):
    """Supported serial framing profiles."""
    SEVEN_EVEN_ONE = "7E1"
    EIGHT_NONE_ONE = "8N1"


class UnitEnum(str, Enum):
    """Distance units."""
    MM = "millimeters"
    CM = "centimeters"
    M = "meters"
    KM = "kilometers"
    FT = "feet"
    IN = "inches"


class ConnectionInfo(BaseModel):
    """Available COM port information."""
    port: str
    description: Optional[str] = None


class SessionConnection(BaseModel):
    """Connection for a collection session."""
    port: str
    name: str = Field(..., min_length=1, max_length=50)
    active: bool = True


class SessionConfig(BaseModel):
    """Session configuration."""
    connections: List[SessionConnection]
    mode: MeasurementModeEnum = MeasurementModeEnum.CONTINUOUS
    frequency_hz: float = Field(10.0, gt=0, le=100)
    baud_rate: int = Field(19200)
    serial_profile: SerialProfileEnum = SerialProfileEnum.SEVEN_EVEN_ONE
    measuring_mode: MeasuringModeEnum = MeasuringModeEnum.NORMAL
    unit: UnitEnum = UnitEnum.MM
    decimal_places: int = Field(4, ge=1, le=10)
    export_csv: bool = True
    rows_per_file: int = Field(10000, ge=1, le=1_000_000)

    @model_validator(mode="after")
    def validate_collection_limits(self):
        if self.baud_rate not in {9600, 19200, 115200}:
            raise ValueError("baud_rate must be one of: 9600, 19200, 115200")

        effective_max = get_effective_max_hz(self.baud_rate, self.measuring_mode.value)
        if self.frequency_hz > effective_max:
            raise ValueError(
                f"frequency_hz={self.frequency_hz} exceeds supported maximum {effective_max} Hz "
                f"for baud_rate={self.baud_rate} and measuring_mode={self.measuring_mode.value}"
            )
        return self


class SampleRecord(BaseModel):
    """Single sensor reading."""
    timestamp_iso: str
    epoch_ms: int
    value: str  # Combined value+unit string
    connection_name: str
    port: str


class SessionStatus(BaseModel):
    """Current session status."""
    session_id: str
    is_running: bool
    sample_count: int
    start_time: Optional[str] = None
    connections_status: dict  # {"connection_name": "Collecting"|"Ready"|"Error"}


class SessionStartResponse(BaseModel):
    """Response when starting a session."""
    session_id: str
    scheduled_start_epoch_s: float
    wait_seconds: float
    message: str


class RateProbeRequest(BaseModel):
    """Request payload for runtime sample-rate probing."""
    port: str
    sensor_id: int = Field(0, ge=0, le=99)
    baud_rate: int = Field(19200)
    serial_profile: SerialProfileEnum = SerialProfileEnum.SEVEN_EVEN_ONE
    measuring_mode: MeasuringModeEnum = MeasuringModeEnum.NORMAL
    duration_seconds: float = Field(2.5, ge=0.5, le=10.0)

    @model_validator(mode="after")
    def validate_probe_limits(self):
        if self.baud_rate not in {9600, 19200, 115200}:
            raise ValueError("baud_rate must be one of: 9600, 19200, 115200")
        return self


class ConnectionDoctorRequest(BaseModel):
    """Request payload for serial settings diagnosis on one port."""
    port: str
    sensor_id: int = Field(0, ge=0, le=99)
    current_baud_rate: int = Field(19200)
    current_serial_profile: SerialProfileEnum = SerialProfileEnum.SEVEN_EVEN_ONE

    @model_validator(mode="after")
    def validate_settings(self):
        if self.current_baud_rate not in {9600, 19200, 115200}:
            raise ValueError("current_baud_rate must be one of: 9600, 19200, 115200")
        return self


class ConnectionDoctorAttempt(BaseModel):
    """One attempted serial combination during diagnosis."""
    baud_rate: int
    serial_profile: str
    success: bool
    detail: str | None = None


class ConnectionDoctorResponse(BaseModel):
    """Diagnosis result with optional recommendation."""
    port: str
    sensor_id: int
    attempted: list[ConnectionDoctorAttempt]
    recommended_baud_rate: int | None = None
    recommended_serial_profile: str | None = None
    summary: str
