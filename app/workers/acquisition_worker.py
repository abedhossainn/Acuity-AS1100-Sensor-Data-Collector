"""Background worker thread for sensor data acquisition."""

from datetime import datetime
from typing import Optional
import time

from PySide6.QtCore import QThread, Signal

from app.domain.models import SampleRecord, MeasurementMode
from app.sensor.serial_client import AcuitySensorClient
from app.sensor.parsing import parse_distance_response, is_error_response
from app.domain.conversion import convert_0p1mm_to_unit


class AcquisitionWorker(QThread):
    """
    Background worker thread for sensor data acquisition.
    
    Signals
    -------
    sample_acquired : SampleRecord
        Emitted when a new sample is captured
    measurement_started : str
        Emitted when measurement starts
    measurement_stopped : str
        Emitted when measurement stops
    error_occurred : str
        Emitted on error
    """
    
    sample_acquired = Signal(SampleRecord)
    measurement_started = Signal(str)
    measurement_stopped = Signal(str)
    error_occurred = Signal(str)
    
    def __init__(self, config):
        """
        Initialize acquisition worker.
        
        Parameters
        ----------
        config : CollectionConfig
            Configuration for data collection
        """
        super().__init__()
        self.config = config
        self.client = AcuitySensorClient(
            port=config.port,
            baudrate=config.baudrate,
            timeout=config.timeout,
            sensor_id=config.sensor_id,
            debug=False,
        )
        self._is_running = False
        self._should_stop = False
    
    def run(self) -> None:
        """Main worker thread loop."""
        try:
            if not self.client.connect():
                self.error_occurred.emit("Failed to connect to sensor")
                return
            
            if self.config.mode == MeasurementMode.CONTINUOUS:
                self._run_continuous()
            elif self.config.mode == MeasurementMode.SINGLE:
                self._run_single()
            
        except Exception as e:
            self.error_occurred.emit(f"Acquisition error: {str(e)}")
        finally:
            self.client.disconnect()
            self._is_running = False
    
    def _run_continuous(self) -> None:
        """
        Run continuous measurement mode using s0h sensor streaming with
        strict host-clock phase-locked decimation.

        Instead of polling with s0g (which has a full command round-trip
        cost every sample and can never exceed the sensor's single-shot
        latency), we:

          1. Send s0h to start the sensor's continuous streaming mode.  In
             this mode the sensor pushes distance lines as fast as it can
             measure, with no per-sample command overhead.

          2. Run a tight loop that reads any available bytes from the serial
             buffer immediately (non-blocking) and keeps the *latest valid
             measurement* in memory.

          3. Use a perf_counter phase-locked timer to emit one sample at
             exactly the user-requested interval.  The emitted value is always
             the most-recent measurement received before that tick.

        This decouples emission rate (host clock — always exact) from sensor
        measurement rate (physics limited).  For a slow or far target the
        user still receives samples at exactly the requested Hz; each sample
        simply reflects the latest available reading at that moment.
        """
        self._is_running = True
        interval = (
            1.0 / self.config.interval_hz
            if self.config.interval_hz and self.config.interval_hz > 0
            else 0.1
        )

        # Start sensor continuous streaming (s0h)
        self.client.clear_input_buffer()
        if not self.client.send_command(self.client._cmd("h")):
            self.error_occurred.emit("Failed to start continuous tracking")
            return
        # Consume the ACK line (g0?) before reading measurement data
        self.client.read_response(wait_time=1.0)

        self.measurement_started.emit(
            f"Collection started at {self.config.interval_hz} Hz "
            f"({interval * 1000:.0f} ms interval)"
        )

        latest_raw: Optional[int] = None
        latest_response: Optional[str] = None
        line_buf = ""
        next_emit = time.perf_counter() + interval

        try:
            while self._is_running and not self._should_stop:
                # ── 1. Drain the serial receive buffer (non-blocking) ──
                chunk = self.client.read_stream_chunk()
                if chunk:
                    line_buf += chunk
                    # Parse all complete CRLF-terminated lines in the buffer
                    while "\n" in line_buf:
                        line, line_buf = line_buf.split("\n", 1)
                        line = line.strip()
                        if line and not is_error_response(line):
                            raw = parse_distance_response(line)
                            if raw is not None:
                                latest_raw = raw
                                latest_response = line

                # ── 2. Emit on the host-clock tick ──
                now = time.perf_counter()
                if now >= next_emit:
                    if latest_raw is not None:
                        sample = self._create_sample_record(
                            latest_raw, latest_response
                        )
                        self.sample_acquired.emit(sample)

                    # Advance phase by one interval (not now+interval) so
                    # timing never drifts even if the loop is occasionally slow.
                    next_emit += interval
                    # Safety: if we've fallen >2 intervals behind, re-anchor.
                    if time.perf_counter() > next_emit + interval:
                        next_emit = time.perf_counter() + interval

                # ── 3. Sleep 1 ms — much shorter than any target interval ──
                # This keeps CPU free while still reacting within 1-2 ms of
                # the emission tick.  Even 10 Hz (100 ms interval) has 100×
                # headroom over this sleep.
                time.sleep(0.001)

        finally:
            # Stop the sensor stream before the port is released
            self.client.stop_measurement()
            self.measurement_stopped.emit("Collection stopped")
    
    def _run_single(self) -> None:
        """Run single measurement mode (one measurement per start)."""
        try:
            self._is_running = True
            
            response = self.client.get_single_measurement()
            
            if response:
                raw_value = parse_distance_response(response)
                if raw_value is not None:
                    sample = self._create_sample_record(raw_value, response)
                    self.sample_acquired.emit(sample)
        
        finally:
            self.measurement_stopped.emit("Single measurement completed")
    
    def _create_sample_record(self, raw_value: int, response: str) -> SampleRecord:
        """
        Create a sample record with timestamp and converted value.
        
        Parameters
        ----------
        raw_value : int
            Raw sensor value (0.1 mm units)
        response : str
            Raw sensor response
        
        Returns
        -------
        SampleRecord
            Complete sample record
        """
        now = datetime.now()
        timestamp_iso = now.isoformat()
        epoch_ms = int(now.timestamp() * 1000)
        
        converted_value = convert_0p1mm_to_unit(raw_value, self.config.unit)
        
        return SampleRecord(
            timestamp_iso=timestamp_iso,
            epoch_ms=epoch_ms,
            raw_0p1mm=raw_value,
            value=converted_value,
            unit=self.config.unit.value,
            mode=self.config.mode.value,
            interval_hz=self.config.interval_hz if self.config.interval_hz > 0 else None,
            sensor_id=self.config.sensor_id,
            response=response,
        )
    
    def stop(self) -> None:
        """Signal worker to stop."""
        self._should_stop = True
        self._is_running = False
        self.wait()
    
    def is_running(self) -> bool:
        """Check if worker is running."""
        return self._is_running
