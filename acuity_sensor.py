"""
Acuity AS1100 Laser Sensor Serial Communication Script

This script connects to an Acuity AS1100 laser sensor via serial port
and provides functions to read data from the device.
"""

import serial
import serial.tools.list_ports
import time


AS1100_ERROR_CODES = {
    200: "Sensor boot in error stack (informational)",
    203: "Wrong command or syntax",
    210: "Sensor not in tracking mode",
    211: "Tracking measurement time too short for conditions",
    212: "Command not allowed while tracking active",
    220: "Serial communication error",
    230: "Distance value overflow",
    233: "Number cannot be displayed",
    234: "Distance not in measurement range",
    236: "DI1/DO1 configuration conflict",
    252: "Temperature too high",
    253: "Temperature too low",
    255: "Signal too low",
    256: "Signal too high",
    257: "Signal-to-noise ratio too low",
    258: "Power supply voltage too high",
    259: "Power supply voltage too low",
    260: "Signal unstable",
    261: "Distance spike beyond limit",
    284: "Signal disturbance in laser output",
    290: "Signal disturbance in sensor optics",
    402: "Firmware installation error",
}


class AcuitySensor:
    def __init__(self, port='COM4', baudrate=19200, timeout=1, debug=False, sensor_id=0):
        """
        Initialize connection to Acuity AS1100 laser sensor.
        
        Parameters:
        -----------
        port : str
            Serial port name (default: 'COM4')
        baudrate : int
            Communication speed (default: 19200)
        timeout : float
            Read timeout in seconds (default: 1)
        debug : bool
            Enable debug output (default: False)
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_connection = None
        self.debug = debug
        self.line_ending = '\r\n'  # CRLF required for AS1100
        self.sensor_id = int(sensor_id)

    def _cmd(self, code, params=None):
        base = f"s{self.sensor_id}{code}"
        if params is None:
            return base
        return f"{base}+{params}"

    def format_response(self, response):
        if not response:
            return ""

        text = response.strip()

        if text.startswith(f"g{self.sensor_id}g+"):
            try:
                value_01mm = int(text.split("+")[1])
                return f"{text}  ({value_01mm / 10:.1f} mm)"
            except Exception:
                return text

        if text.startswith(f"g{self.sensor_id}m+"):
            return f"{text}  (signal strength)"

        if text.startswith(f"g{self.sensor_id}t+"):
            try:
                value_01c = int(text.split("+")[1])
                return f"{text}  ({value_01c / 10:.1f} °C)"
            except Exception:
                return text

        if text.startswith(f"g{self.sensor_id}sv+"):
            payload = text.split("+")[1]
            if len(payload) >= 8:
                measure_fw = payload[:4]
                iface_fw = payload[4:8]
                return f"{text}  (measure fw: {measure_fw}, interface fw: {iface_fw})"
            return text

        if text.startswith(f"g{self.sensor_id}re+"):
            codes = []
            try:
                codes = [int(part) for part in text.split("+")[1:]]
            except Exception:
                return text
            if not codes:
                return text
            decoded = "; ".join(f"{code}: {AS1100_ERROR_CODES.get(code, 'Unknown')}" for code in codes)
            return f"{text}\nDecoded: {decoded}"

        if text.startswith(f"g{self.sensor_id}@E"):
            try:
                code = int(text.split("@E")[1])
                meaning = AS1100_ERROR_CODES.get(code, "Unknown error")
                return f"{text}  ({meaning})"
            except Exception:
                return text

        return text
        
    def connect(self):
        """Establish serial connection to the sensor."""
        try:
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.SEVENBITS,  # 7 data bits
                parity=serial.PARITY_EVEN,   # Even parity
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout
            )
            time.sleep(0.5)  # Allow time for connection to stabilize
            print(f"Successfully connected to {self.port}")
            print(f"Settings: {self.baudrate} Baud, 7 Data bits, Parity Even")
            return True
        except serial.SerialException as e:
            print(f"Error connecting to {self.port}: {e}")
            return False
    
    def disconnect(self):
        """Close the serial connection."""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            print(f"Disconnected from {self.port}")
    
    def is_connected(self):
        """Check if the serial connection is active."""
        return self.serial_connection and self.serial_connection.is_open
    
    def send_command(self, command, line_ending=None):
        """
        Send a command to the sensor.
        
        Parameters:
        -----------
        command : str
            Command string to send to the sensor
        line_ending : str, optional
            Line ending to use (overrides default)
        """
        if not self.is_connected():
            print("Error: Not connected to sensor")
            return False
        
        try:
            # Use specified line ending or default
            ending = line_ending if line_ending is not None else self.line_ending
            
            # Strip any existing line endings and add the desired one
            command = command.rstrip('\r\n') + ending
            
            cmd_bytes = command.encode('ascii')
            self.serial_connection.write(cmd_bytes)
            self.serial_connection.flush()
            
            if self.debug:
                print(f"[DEBUG] Sent: {repr(command)} ({len(cmd_bytes)} bytes)")
                print(f"[DEBUG] Hex: {cmd_bytes.hex(' ')}")
            
            return True
        except Exception as e:
            print(f"Error sending command: {e}")
            return False
    
    def read_response(self, num_bytes=None, wait_time=0.5):
        """
        Read response from the sensor.
        
        Parameters:
        -----------
        num_bytes : int, optional
            Number of bytes to read. If None, reads all available data.
        wait_time : float
            Time to wait for response (default: 0.5s)
        
        Returns:
        --------
        str : Response from the sensor
        """
        if not self.is_connected():
            print("Error: Not connected to sensor")
            return None
        
        try:
            # Wait for data to arrive
            time.sleep(wait_time)
            
            # Check how many bytes are waiting
            bytes_waiting = self.serial_connection.in_waiting
            
            if self.debug:
                print(f"[DEBUG] Bytes waiting: {bytes_waiting}")
            
            if bytes_waiting == 0:
                return None
            
            # Read the available data
            if num_bytes:
                data = self.serial_connection.read(num_bytes)
            else:
                data = self.serial_connection.read(bytes_waiting)
            
            if self.debug:
                print(f"[DEBUG] Received: {repr(data)} ({len(data)} bytes)")
                print(f"[DEBUG] Hex: {data.hex(' ')}")
            
            return data.decode('ascii', errors='ignore').strip()
        except Exception as e:
            print(f"Error reading response: {e}")
            return None
    
    def read_measurement(self, wait_time=0.2):
        """
        Read available data from the sensor without clearing input buffer.
        
        Returns:
        --------
        str : Measurement data from the sensor
        """
        if not self.is_connected():
            print("Error: Not connected to sensor")
            return None
        
        try:
            time.sleep(wait_time)
            # Read available data
            if self.serial_connection.in_waiting > 0:
                data = self.serial_connection.read(self.serial_connection.in_waiting)
                return data.decode('ascii', errors='ignore').strip()
            else:
                return None
        except Exception as e:
            print(f"Error reading measurement: {e}")
            return None
    
    def clear_buffers(self):
        """Clear input and output buffers."""
        if self.is_connected():
            self.serial_connection.reset_input_buffer()
            self.serial_connection.reset_output_buffer()

    def clear_input_buffer(self):
        if self.is_connected():
            self.serial_connection.reset_input_buffer()
    
    # === Acuity AS Series Sensor Commands ===
    
    def start_continuous_measurement(self):
        """
        Start continuous measurement mode.
        Sensor will continuously output distance measurements.
        """
        print("Starting continuous measurement mode...")
        self.clear_input_buffer()
        return self.send_command(self._cmd("h"))
    
    def trigger_measurement(self):
        """
        Trigger a single measurement.
        Use this for on-demand readings.
        """
        self.clear_input_buffer()
        return self.send_command(self._cmd("g"))
    
    def stop_measurement(self):
        """
        Stop continuous measurement mode.
        """
        print("Stopping measurements...")
        return self.send_command(self._cmd("c"))
    
    def get_sensor_info(self):
        """
        Request sensor information.
        """
        self.clear_input_buffer()
        self.send_command(self._cmd("sn"))
        time.sleep(0.2)
        return self.read_response()
    
    def get_version(self):
        """
        Get sensor firmware version.
        """
        self.clear_input_buffer()
        self.send_command(self._cmd("sv"))
        time.sleep(0.2)
        return self.read_response()
    
    def set_output_mode(self, mode='A'):
        """
        Set output mode.
        Parameters:
        -----------
        mode : str
            'A' - ASCII output (default)
            'B' - Binary output
        """
        cmd = self._cmd("uo", str(mode))
        return self.send_command(cmd)
    
    def test_communication(self):
        """
        Test basic communication with the sensor.
        Tries various common commands and line endings.
        """
        print("\n" + "=" * 60)
        print("TESTING COMMUNICATION")
        print("=" * 60)
        
        # Test different line endings
        line_endings = [
            ('\r', 'CR'),
            ('\n', 'LF'),
            ('\r\n', 'CRLF'),
            ('', 'None'),
        ]
        
        test_commands = [
            (self._cmd("sn"), "Serial number"),
            (self._cmd("sv"), "Firmware version"),
            (self._cmd("g"), "Single distance measurement"),
            (self._cmd("m", "0"), "Single signal strength measurement"),
            (self._cmd("t"), "Single temperature measurement"),
            (self._cmd("re"), "Read error stack"),
        ]
        
        print(f"\n1. Testing different line endings with '{self._cmd('sn')}' command:")
        for ending, name in line_endings:
            print(f"\n  Trying {name} ({repr(ending)}):")
            self.clear_buffers()
            self.send_command(self._cmd("sn"), line_ending=ending)
            response = self.read_response(wait_time=0.5)
            if response:
                print(f"    ✓ Response: {response}")
                print(f"    [Found working line ending: {name}]")
                self.line_ending = ending
                break
            else:
                print(f"    ✗ No response")
        
        # Check if sensor is already streaming data
        print("\n2. Checking for automatic/streaming output...")
        self.clear_buffers()
        time.sleep(2)  # Wait longer
        if self.serial_connection.in_waiting > 0:
            data = self.serial_connection.read(min(100, self.serial_connection.in_waiting))
            print(f"  ✓ Receiving data: {repr(data)}")
            print(f"  Hex: {data.hex(' ')}")
        else:
            print(f"  ✗ No automatic output detected")
        
        # Try standard AS1100 commands with selected line ending
        print("\n3. Testing AS1100 commands...")
        for cmd, description in test_commands:
            print(f"\n  {description}: {cmd}")
            self.clear_input_buffer()
            self.send_command(cmd)
            response = self.read_response(wait_time=0.6)
            if response:
                print(f"    ✓ Response: {response}")
            else:
                print("    ✗ No response")

        # Try reading DTR/RTS
        print("\n4. Testing hardware flow control...")
        try:
            print(f"  DTR: {self.serial_connection.dtr}")
            print(f"  RTS: {self.serial_connection.rts}")
            print("  Trying DTR=True, RTS=True...")
            self.serial_connection.dtr = True
            self.serial_connection.rts = True
            time.sleep(0.5)
            self.send_command(self._cmd("sn"))
            response = self.read_response(wait_time=0.5)
            if response:
                print(f"  ✓ Response with DTR/RTS: {response}")
        except Exception as e:
            print(f"  Error: {e}")
        
        print("\n" + "=" * 60)
    
    def raw_monitor(self, duration=10):
        """
        Monitor raw serial data for a specified duration.
        Useful for debugging when sensor might be sending data unexpectedly.
        
        Parameters:
        -----------
        duration : int
            How long to monitor in seconds
        """
        print(f"\nMonitoring raw serial data for {duration} seconds...")
        print("Press Ctrl+C to stop early\n")
        
        start_time = time.time()
        data_received = False
        
        try:
            while (time.time() - start_time) < duration:
                if self.serial_connection.in_waiting > 0:
                    data = self.serial_connection.read(self.serial_connection.in_waiting)
                    data_received = True
                    print(f"[{time.time() - start_time:.2f}s] Received {len(data)} bytes:")
                    print(f"  ASCII: {repr(data)}")
                    print(f"  Hex: {data.hex(' ')}")
                    try:
                        decoded = data.decode('ascii', errors='replace')
                        print(f"  Decoded: {decoded}")
                    except:
                        pass
                time.sleep(0.1)
            
            if not data_received:
                print("No data received during monitoring period.")
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user.")


def list_available_ports():
    """List all available serial ports."""
    ports = serial.tools.list_ports.comports()
    print("Available serial ports:")
    for port in ports:
        print(f"  {port.device} - {port.description}")
    return [port.device for port in ports]


def print_menu(debug_mode):
    """Print interactive menu."""
    print("\n" + "=" * 60)
    print("SENSOR CONTROL MENU")
    print("=" * 60)
    print("1. Start continuous tracking (s#h)")
    print("2. Trigger single distance measurement (s#g)")
    print("3. Stop/Clear (s#c)")
    print("4. Read serial number (s#sn)")
    print("5. Read firmware version (s#sv)")
    print("6. Read data continuously")
    print("7. Send custom command")
    print("8. Test communication")
    print("9. Raw monitor (listen for any data)")
    print(f"D. Toggle debug mode (currently: {'ON' if debug_mode else 'OFF'})")
    print("Q. Quit")
    print("=" * 60)


def main():
    """Main function demonstrating sensor usage."""
    print("=" * 60)
    print("Acuity AS1100 Laser Sensor - Serial Communication")
    print("=" * 60)
    print()
    
    # List available ports
    list_available_ports()
    print()
    
    # Create sensor instance with debug mode
    sensor = AcuitySensor(port='COM4', baudrate=19200, timeout=2, debug=False, sensor_id=0)
    
    try:
        # Connect to sensor
        if sensor.connect():
            print("\nConnection established!")
            
            # Interactive menu loop
            while True:
                print_menu(sensor.debug)
                choice = input("\nEnter your choice: ").strip().upper()
                
                if choice == '1':
                    sensor.start_continuous_measurement()
                    first_reply = sensor.read_response(wait_time=0.6)
                    if first_reply:
                        print(f"Start reply: {first_reply}")
                    print("\nContinuous mode activated. Reading measurements...")
                    print("Press Ctrl+C to return to menu\n")
                    try:
                        while True:
                            measurement = sensor.read_measurement()
                            if measurement:
                                print(f"Measurement: {measurement}")
                            time.sleep(0.1)
                    except KeyboardInterrupt:
                        print("\n\nReturning to menu...")
                        sensor.stop_measurement()
                
                elif choice == '2':
                    print("\nTriggering single measurement...")
                    sensor.trigger_measurement()
                    measurement = sensor.read_response(wait_time=0.6)
                    if measurement:
                        print(f"Measurement: {sensor.format_response(measurement)}")
                    else:
                        print("No measurement received")
                
                elif choice == '3':
                    sensor.stop_measurement()
                    print("Measurements stopped")
                
                elif choice == '4':
                    print("\nReading serial number...")
                    info = sensor.get_sensor_info()
                    if info:
                        print(f"Serial Number: {sensor.format_response(info)}")
                    else:
                        print("No response received")
                
                elif choice == '5':
                    print("\nGetting version...")
                    version = sensor.get_version()
                    if version:
                        print(f"Version: {sensor.format_response(version)}")
                    else:
                        print("No response received")
                
                elif choice == '6':
                    print("\nReading data continuously...")
                    print("Press Ctrl+C to return to menu\n")
                    try:
                        while True:
                            measurement = sensor.read_measurement()
                            if measurement:
                                print(f"Data: {measurement}")
                            time.sleep(0.1)
                    except KeyboardInterrupt:
                        print("\n\nReturning to menu...")
                
                elif choice == '7':
                    cmd = input("Enter full command (example s0g): ").strip()
                    sensor.send_command(cmd)
                    response = sensor.read_response(wait_time=0.6)
                    if response:
                        print(f"Response: {sensor.format_response(response)}")
                    else:
                        print("No response received")
                
                elif choice == '8':
                    sensor.test_communication()
                
                elif choice == '9':
                    duration = input("Monitor duration in seconds (default 10): ").strip()
                    try:
                        duration = int(duration) if duration else 10
                    except ValueError:
                        duration = 10
                    sensor.raw_monitor(duration)
                
                elif choice == 'D':
                    sensor.debug = not sensor.debug
                    print(f"\nDebug mode: {'ON' if sensor.debug else 'OFF'}")
                
                elif choice == 'Q':
                    break
                
                else:
                    print("Invalid choice. Please try again.")
                
    except KeyboardInterrupt:
        print("\n\nStopping...")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        # Always disconnect when done
        sensor.disconnect()
        print("Program terminated.")


if __name__ == "__main__":
    main()
