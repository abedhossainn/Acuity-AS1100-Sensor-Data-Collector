"""AS1100 sensor serial communication client."""

import time
import serial
import serial.tools.list_ports
from typing import List, Optional


SUPPORTED_SERIAL_PROFILES: tuple[str, ...] = ("7E1", "8N1")


def _normalize_serial_profile(serial_profile: str) -> str:
    profile = str(serial_profile).strip().upper()
    return profile if profile in SUPPORTED_SERIAL_PROFILES else "7E1"


def _serial_profile_params(serial_profile: str) -> tuple[int, str, float]:
    profile = _normalize_serial_profile(serial_profile)
    if profile == "8N1":
        return serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE
    # Default profile for AS1100 legacy compatibility.
    return serial.SEVENBITS, serial.PARITY_EVEN, serial.STOPBITS_ONE


class AcuitySensorClient:
    """
    Low-level serial communication client for AS1100 sensor.
    Extracted and simplified from acuity_sensor.py.
    """
    
    def __init__(
        self,
        port: str,
        baudrate: int = 19200,
        timeout: float = 3.0,
        sensor_id: int = 0,
        debug: bool = False,
        serial_profile: str = "7E1",
    ):
        """
        Initialize AS1100 sensor client.
        
        Parameters
        ----------
        port : str
            Serial port name (e.g., "COM4")
        baudrate : int
            Communication speed (default 19200)
        timeout : float
            Read timeout in seconds (default 3.0 for far-distance measurements)
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
        self.serial_profile = _normalize_serial_profile(serial_profile)
        self.line_ending = "\r\n"  # CRLF required for AS1100
        self.serial_connection: Optional[serial.Serial] = None
        self.last_connect_error: str = ""
    
    def _cmd(self, code: str, params: Optional[str] = None) -> str:
        """Build AS1100 command string."""
        base = f"s{self.sensor_id}{code}"
        if params is None:
            return base
        return f"{base}+{params}"
    
    def connect(self) -> bool:
        """
        Establish serial connection and verify the sensor is actually responding.
        
        Returns True only if the port opens AND the sensor replies to a serial
        number query with a valid response. Returns False if the port cannot be
        opened or if the sensor does not respond (e.g. powered off).
        """
        self.last_connect_error = ""
        try:
            bytesize, parity, stopbits = _serial_profile_params(self.serial_profile)
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=bytesize,
                parity=parity,
                stopbits=stopbits,
                timeout=self.timeout,
            )
            # Give sensor time to initialize after port open
            time.sleep(2.0)

            # Clear any stale data
            self.clear_input_buffer()

            # Send STOP first to reset sensor state - required before any other command
            stop_cmd = self._cmd("c") + self.line_ending
            self.serial_connection.write(stop_cmd.encode("ascii"))
            self.serial_connection.flush()
            time.sleep(1.0)
            self.clear_input_buffer()  # discard g0? or any stop response

            # Verify the sensor is actually responding by querying serial number
            sn_cmd = self._cmd("sn") + self.line_ending
            self.serial_connection.write(sn_cmd.encode("ascii"))
            self.serial_connection.flush()
            time.sleep(1.0)
            raw = b""
            deadline = time.monotonic() + self.timeout
            while time.monotonic() < deadline:
                if self.serial_connection.in_waiting > 0:
                    raw += self.serial_connection.read(self.serial_connection.in_waiting)
                    if b"\n" in raw:
                        break
                time.sleep(0.05)

            response = raw.decode("ascii", errors="ignore").strip()
            expected_prefix = f"g{self.sensor_id}sn+"
            if not response.startswith(expected_prefix):
                # Sensor did not reply with a valid serial number — not connected
                if not response:
                    self.last_connect_error = (
                        "No sensor response to serial number query; "
                        "possible baud/profile mismatch, no sensor power, or wrong COM port"
                    )
                else:
                    self.last_connect_error = (
                        f"Unexpected sensor response during verification: {response!r}"
                    )
                if self.debug:
                    print(f"Sensor verification failed. Got: {response!r}")
                self.serial_connection.close()
                self.serial_connection = None
                return False

            if self.debug:
                print(
                    f"Connected to {self.port}: {self.baudrate} baud, profile={self.serial_profile}"
                )
                print(f"Sensor confirmed: {response}")
            return True
        except serial.SerialException as e:
            self.last_connect_error = str(e)
            if self.debug:
                print(f"Connection error: {e}")
            if self.serial_connection:
                try:
                    self.serial_connection.close()
                except:
                    pass
                self.serial_connection = None
            return False
        except Exception as e:
            self.last_connect_error = str(e)
            if self.serial_connection:
                try:
                    self.serial_connection.close()
                except:
                    pass
                self.serial_connection = None
            return False
    
    def disconnect(self) -> None:
        """Close serial connection."""
        if self.serial_connection and self.serial_connection.is_open:
            # Flush buffers before closing
            try:
                self.serial_connection.reset_input_buffer()
                self.serial_connection.reset_output_buffer()
                self.serial_connection.flush()
            except:
                pass
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
    
    def read_response(self, wait_time: float = 2.0) -> Optional[str]:
        """
        Read response from sensor by polling until a complete line arrives.

        Returns as soon as a CRLF-terminated line is received, not after a
        fixed sleep.  This means fast sensor responses are captured immediately
        and slow ones are waited on up to `wait_time` seconds.
        
        Parameters
        ----------
        wait_time : float
            Maximum time to wait for a response (default 2.0 s).
            Returns whatever is buffered if timeout is reached.
        
        Returns
        -------
        str or None
            Response string or None if no data arrived within the timeout
        """
        if not self.is_connected():
            return None
        
        try:
            deadline = time.perf_counter() + wait_time
            buffer = b""
            while time.perf_counter() < deadline:
                waiting = self.serial_connection.in_waiting
                if waiting > 0:
                    buffer += self.serial_connection.read(waiting)
                    if b"\n" in buffer:          # complete AS1100 response line
                        break
                else:
                    time.sleep(0.005)           # 5 ms poll — no missed bytes

            if not buffer:
                return None

            response = buffer.decode("ascii", errors="ignore").strip()
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
    
    def get_measurement(self) -> Optional[str]:
        """
        Request one distance measurement sample.
        
        Returns
        -------
        str or None
            Response string (g#g+aaaaaaaa) or None
        """
        self.clear_input_buffer()
        if self.send_command(self._cmd("g")):
            return self.read_response(wait_time=1.5)  # Increased from 0.6 for far-distance
        return None

    def get_single_measurement(self) -> Optional[str]:
        """Backward-compatible alias for get_measurement()."""
        return self.get_measurement()
    
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
            return self.read_response(wait_time=1.0)  # Increased from 0.6
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
            return self.read_response(wait_time=1.0)  # Increased from 0.6
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
            return self.read_response(wait_time=0.8)  # Increased from 0.5
        return None
    
    def read_serial_number(self) -> Optional[str]:
        """Read sensor serial number."""
        self.clear_input_buffer()
        if self.send_command(self._cmd("sn")):
            return self.read_response(wait_time=1.0)  # Increased from 0.6
        return None
    
    def read_firmware_version(self) -> Optional[str]:
        """Read sensor firmware version."""
        self.clear_input_buffer()
        if self.send_command(self._cmd("sv")):
            return self.read_response(wait_time=1.0)  # Increased from 0.6
        return None

    def set_measuring_mode(self, mode_code: int) -> bool:
        """Set measuring mode using AS1100 command s#mc+a."""
        self.clear_input_buffer()
        if self.send_command(self._cmd("mc", str(int(mode_code)))):
            response = self.read_response(wait_time=1.0)
            return bool(response)
        return False
    
    def laser_on(self) -> Optional[str]:
        """Turn laser on (AS1100 'o') and return one measurement sample if available."""
        self.clear_input_buffer()
        if self.send_command(self._cmd("o")):
            # Read/clear ON acknowledgement first (often g0?)
            on_response = self.read_response(wait_time=0.8)

            # Then request one distance sample so UI can still display value
            self.clear_input_buffer()
            if self.send_command(self._cmd("g")):
                response = self.read_response(wait_time=1.5)
            else:
                response = None

            if self.debug:
                print(f"Laser ON + measurement response: {response}")
            return response if response else on_response
        return None
    
    def laser_off(self) -> Optional[str]:
        """Send stop/idle command (AS1100 'c' command)."""
        if self.send_command(self._cmd("c")):
            response = self.read_response(wait_time=0.8)
            if self.debug:
                print(f"Stop response: {response}")
            return response
        return None
    
    def read_stream_chunk(self) -> Optional[str]:
        """
        Read whatever bytes are currently in the receive buffer, immediately,
        without waiting.  Used by the streaming acquisition loop so the loop
        can drain new data each iteration without introducing any delay.

        Returns
        -------
        str or None
            Raw ASCII string (may contain partial lines) or None if buffer empty.
        """
        if not self.is_connected():
            return None
        try:
            waiting = self.serial_connection.in_waiting
            if waiting > 0:
                data = self.serial_connection.read(waiting)
                return data.decode("ascii", errors="ignore")
            return None
        except Exception:
            return None

    @staticmethod
    def list_ports() -> List[str]:
        """List all available serial ports."""
        ports = []
        for port_info in serial.tools.list_ports.comports():
            ports.append(port_info.device)
        return ports

    @staticmethod
    def list_ports_detailed() -> List[dict]:
        """List available serial ports with metadata."""
        ports: List[dict] = []
        for port_info in serial.tools.list_ports.comports():
            ports.append(
                {
                    "port": port_info.device,
                    "description": port_info.description,
                    "hwid": port_info.hwid,
                }
            )
        return ports

    @staticmethod
    def get_port_device(port_string: str) -> str:
        """Extract device name from port string (handles 'COM3' and 'COM3 - Description')."""
        if " - " in port_string:
            return port_string.split(" - ")[0].strip()
        return port_string.strip()
