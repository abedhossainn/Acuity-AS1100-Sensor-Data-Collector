"""
Direct sensor diagnostic test.
Bypasses AcuitySensorClient to test raw serial communication.
Run: python diagnose_sensor.py
"""

import time
import serial
import serial.tools.list_ports
import sys


def list_ports():
    ports = serial.tools.list_ports.comports()
    print("\n=== Available COM Ports ===")
    for p in ports:
        print(f"  {p.device} - {p.description}")
    return [p.device for p in ports]


def raw_send(ser, command: str, label: str, wait: float = 2.0):
    """Send command and read raw response."""
    # Clear buffer first
    ser.reset_input_buffer()
    time.sleep(0.1)

    cmd = command + "\r\n"
    print(f"\n--- {label} ---")
    print(f"  TX: {repr(cmd)}")
    ser.write(cmd.encode("ascii"))
    ser.flush()

    time.sleep(wait)

    raw = b""
    while ser.in_waiting:
        raw += ser.read(ser.in_waiting)
        time.sleep(0.05)

    if raw:
        text = raw.decode("ascii", errors="replace").strip()
        print(f"  RX: {repr(text)}")
        print(f"  OK: {text}")
        return text
    else:
        print(f"  RX: <no response>")
        return None


def run_diagnostics(port: str):
    print(f"\n{'='*50}")
    print(f" AS1100 SENSOR DIAGNOSTIC")
    print(f" Port: {port}")
    print(f"{'='*50}")

    try:
        print(f"\nOpening {port} at 19200 baud, 7E1...")
        ser = serial.Serial(
            port=port,
            baudrate=19200,
            bytesize=serial.SEVENBITS,
            parity=serial.PARITY_EVEN,
            stopbits=serial.STOPBITS_ONE,
            timeout=3.0,
        )
        print(f"  Port open: {ser.is_open}")
        print(f"  Settings: {ser}")

        # STEP 1: Allow sensor to settle after opening
        print("\n[1] Waiting 2s for sensor to settle after port open...")
        time.sleep(2.0)
        ser.reset_input_buffer()
        print("    Buffer cleared.")

        # STEP 2: Check if anything arrives unsolicited
        print("\n[2] Listening for 1s for unsolicited data...")
        time.sleep(1.0)
        if ser.in_waiting:
            data = ser.read(ser.in_waiting).decode("ascii", errors="replace").strip()
            print(f"    Unsolicited: {repr(data)}")
        else:
            print("    (nothing received)")
        ser.reset_input_buffer()

        # STEP 3: Send STOP first to clear any ongoing tracking
        print("\n[3] Sending STOP (s0c) to clear any existing state...")
        raw_send(ser, "s0c", "STOP", wait=1.5)
        time.sleep(0.5)
        ser.reset_input_buffer()

        # STEP 4: Serial number
        print("\n[4] Requesting serial number (s0sn)...")
        sn = raw_send(ser, "s0sn", "SERIAL NUMBER", wait=2.0)

        # STEP 5: Firmware version
        print("\n[5] Requesting firmware version (s0sv)...")
        fw = raw_send(ser, "s0sv", "FIRMWARE", wait=2.0)

        # STEP 6: Single measurement
        print("\n[6] Requesting single measurement (s0g)...")
        meas = raw_send(ser, "s0g", "SINGLE MEASUREMENT", wait=2.0)

        # STEP 7: Continuous (a few samples)
        print("\n[7] Starting continuous tracking (s0h)...")
        raw_send(ser, "s0h", "START CONTINUOUS", wait=2.0)
        print("    Reading 5 seconds of continuous data...")
        start = time.time()
        lines_received = 0
        while time.time() - start < 5.0:
            if ser.in_waiting:
                raw = ser.read(ser.in_waiting).decode("ascii", errors="replace").strip()
                for line in raw.split():
                    if line:
                        print(f"    Sample: {line}")
                        lines_received += 1
            time.sleep(0.1)
        print(f"    Total samples received: {lines_received}")

        # STEP 8: Stop continuous
        print("\n[8] Stopping continuous tracking (s0c)...")
        raw_send(ser, "s0c", "STOP CONTINUOUS", wait=1.0)

        ser.close()
        print(f"\n{'='*50}")
        print(" DIAGNOSTIC COMPLETE")
        print(f"{'='*50}")

        print("\n=== SUMMARY ===")
        print(f"  Serial number  : {sn or '<none>'}")
        print(f"  Firmware       : {fw or '<none>'}")
        print(f"  Single meas.   : {meas or '<none>'}")
        print(f"  Continuous     : {lines_received} samples in 5 seconds")

        if lines_received == 0 and not meas:
            print("\n  *** PROBLEM: No measurements received. Check sensor power and cable.")
        elif "E212" in str(sn) + str(fw) + str(meas):
            print("\n  *** NOTICE: E212 errors on info commands (normal on some firmware).")
            print("      If continuous/single measurements work, collection will succeed.")

    except serial.SerialException as e:
        print(f"\n  ERROR opening port: {e}")
        sys.exit(1)


if __name__ == "__main__":
    ports = list_ports()

    if len(sys.argv) > 1:
        port = sys.argv[1]
    elif ports:
        port = ports[0]
        # Prefer COM4 if present
        for p in ports:
            if "COM4" in p:
                port = p
                break
        print(f"\nUsing port: {port}")
    else:
        print("\nNo COM ports found. Connect the sensor and try again.")
        sys.exit(1)

    run_diagnostics(port)
