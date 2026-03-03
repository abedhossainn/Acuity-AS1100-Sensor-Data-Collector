"""Background worker thread for sensor data acquisition."""

from datetime import datetime
from typing import Optional
import time

from PySide6.QtCore import QThread, Signal

from app.domain.models import SampleRecord, MeasurementMode, IntervalMode
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
        """Run continuous measurement mode."""
        try:
            self._is_running = True
            
            # Always use basic continuous mode (s#h)
            # Throttling will be done on client side if needed
            response = self.client.start_continuous_tracking()
            
            # Check if startup was successful
            if not response:
                self.error_occurred.emit("No response from sensor when starting measurement")
                return
            
            if is_error_response(response):
                self.error_occurred.emit(f"Sensor error when starting measurement: {response}")
                return
            
            self.measurement_started.emit(f"Continuous tracking started: {response}")
            
            # Acquisition loop with optional client-side throttling
            next_sample_time = time.time()
            
            while self._is_running and not self._should_stop:
                response = self.client.read_available_data(wait_time=0.05)
                
                if response:
                    # Skip error responses
                    if is_error_response(response):
                        continue
                    
                    # Parse and emit sample
                    raw_value = parse_distance_response(response)
                    if raw_value is not None:
                        # Apply client-side throttling if in host-throttled mode
                        if self.config.interval_mode == IntervalMode.HOST_THROTTLED:
                            now = time.time()
                            if self.config.interval_hz > 0:
                                min_interval = 1.0 / self.config.interval_hz
                                if now < next_sample_time:
                                    continue
                                next_sample_time = now + min_interval
                        
                        # Create sample record
                        sample = self._create_sample_record(raw_value, response)
                        self.sample_acquired.emit(sample)
                
                if self._should_stop:
                    break
                
                time.sleep(0.01)
        
        finally:
            self.client.stop_measurement()
            self.measurement_stopped.emit("Continuous tracking stopped")
    
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
