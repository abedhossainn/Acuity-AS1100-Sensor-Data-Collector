"""AS1100 sensor serial communication client."""

import time
import serial
import serial.tools.list_ports
from typing import List, Optional


class AcuitySensorClient:
    """
    Low-level serial communication client for AS1100 sensor.
    Extracted and simplified from acuity_sensor.py.
    """
    
    def __init__(self, port: str, baudrate: int = 19200, timeout: float = 1.0, sensor_id: int = 0, debug: bool = False):
        """
        Initialize AS1100 sensor client.
        
        Parameters
        ----------
        port : str
            Serial port name (e.g., "COM4")
        baudrate : int
            Communication speed (default 19200)
        timeout : float
            Read timeout in seconds
        sensor_id : int
            Sensor ID number (0-99)
        debug : bool
            Enable debug output
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.sensor_id = int(sensor_id)
        self.debug = debug
        self.line_ending = "\r\n"  # CRLF required for AS1100
        self.serial_connection: Optional[serial.Serial] = None
    
    def _cmd(self, code: str, params: Optional[str] = None) -> str:
        """Build AS1100 command string."""
        base = f"s{self.sensor_id}{code}"
        if params is None:
            return base
        return f"{base}+{params}"
    
    def connect(self) -> bool:
        """Establish serial connection."""
        try:
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.SEVENBITS,
                parity=serial.PARITY_EVEN,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout,
            )
            time.sleep(0.5)
            if self.debug:
                print(f"Connected to {self.port}: {self.baudrate} baud, 7 data bits, even parity")
            return True
        except serial.SerialException as e:
            if self.debug:
                print(f"Connection error: {e}")
            return False
    
    def disconnect(self) -> None:
        """Close serial connection."""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            if self.debug:
                print(f"Disconnected from {self.port}")
    
    def is_connected(self) -> bool:
        """Check if serial connection is active."""
        return self.serial_connection is not None and self.serial_connection.is_open
    
    def send_command(self, command: str) -> bool:
        """
        Send command to sensor.
        
        Parameters
        ----------
        command : str
            Command string (e.g., "s0g")
        
        Returns
        -------
        bool
            True if sent successfully
        """
        if not self.is_connected():
            return False
        
        try:
            # Strip and add line ending
            command = command.rstrip("\r\n") + self.line_ending
            cmd_bytes = command.encode("ascii")
            self.serial_connection.write(cmd_bytes)
            self.serial_connection.flush()
            
            if self.debug:
                print(f"[TX] {repr(command)}")
            
            return True
        except Exception as e:
            if self.debug:
                print(f"Send error: {e}")
            return False
    
    def read_response(self, wait_time: float = 0.5) -> Optional[str]:
        """
        Read response from sensor.
        
        Parameters
        ----------
        wait_time : float
            Time to wait for response
        
        Returns
        -------
        str or None
            Response string or None if no data
        """
        if not self.is_connected():
            return None
        
        try:
            time.sleep(wait_time)
            bytes_waiting = self.serial_connection.in_waiting
            
            if bytes_waiting == 0:
                return None
            
            data = self.serial_connection.read(bytes_waiting)
            response = data.decode("ascii", errors="ignore").strip()
            
            if self.debug:
                print(f"[RX] {repr(response)}")
            
            return response
        except Exception as e:
            if self.debug:
                print(f"Read error: {e}")
            return None
    
    def clear_input_buffer(self) -> None:
        """Clear input buffer."""
        if self.is_connected():
            self.serial_connection.reset_input_buffer()
    
    def get_single_measurement(self) -> Optional[str]:
        """
        Request single distance measurement.
        
        Returns
        -------
        str or None
            Response string (g#g+aaaaaaaa) or None
        """
        self.clear_input_buffer()
        if self.send_command(self._cmd("g")):
            return self.read_response(wait_time=0.6)
        return None
    
    def start_continuous_tracking(self) -> Optional[str]:
        """
        Start continuous measurement tracking.
        
        Returns
        -------
        str or None
            Response string or None
        """
        self.clear_input_buffer()
        if self.send_command(self._cmd("h")):
            return self.read_response(wait_time=0.6)
        return None
    
    def start_timed_tracking(self, interval_ms: int) -> Optional[str]:
        """
        Start timed measurement tracking.
        
        Parameters
        ----------
        interval_ms : int
            Sampling interval in milliseconds
        
        Returns
        -------
        str or None
            Response string or None
        """
        self.clear_input_buffer()
        if self.send_command(self._cmd("h", str(interval_ms))):
            return self.read_response(wait_time=0.6)
        return None
    
    def stop_measurement(self) -> Optional[str]:
        """
        Stop measurement/tracking.
        
        Returns
        -------
        str or None
            Response string or None
        """
        if self.send_command(self._cmd("c")):
            return self.read_response(wait_time=0.5)
        return None
    
    def read_serial_number(self) -> Optional[str]:
        """Read sensor serial number."""
        self.clear_input_buffer()
        if self.send_command(self._cmd("sn")):
            return self.read_response(wait_time=0.6)
        return None
    
    def read_firmware_version(self) -> Optional[str]:
        """Read sensor firmware version."""
        self.clear_input_buffer()
        if self.send_command(self._cmd("sv")):
            return self.read_response(wait_time=0.6)
        return None
    
    def read_available_data(self, wait_time: float = 0.1) -> Optional[str]:
        """
        Read data without clearing buffer (for streaming).
        
        Parameters
        ----------
        wait_time : float
            Small wait for new data
        
        Returns
        -------
        str or None
            Available response or None
        """
        if not self.is_connected():
            return None
        
        try:
            time.sleep(wait_time)
            if self.serial_connection.in_waiting > 0:
                data = self.serial_connection.read(self.serial_connection.in_waiting)
                return data.decode("ascii", errors="ignore").strip()
            return None
        except Exception:
            return None
    
    @staticmethod
    def list_ports() -> List[str]:
        """List available serial ports."""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
