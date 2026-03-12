"""
Integration test using AcuitySensorClient.
Tests the full stack: connect → query info → single measurement → continuous → disconnect.
Run: python test_sensor_integration.py [COM4]
"""

import sys
import time

from app.sensor.serial_client import AcuitySensorClient
from app.sensor.parsing import parse_distance_response, is_error_response
from app.domain.models import Unit
from app.domain.conversion import convert_0p1mm_to_unit


def run(port: str):
    passed = 0
    failed = 0

    def ok(msg):
        nonlocal passed
        passed += 1
        print(f"  [PASS] {msg}")

    def fail(msg):
        nonlocal failed
        failed += 1
        print(f"  [FAIL] {msg}")

    print(f"\n{'='*55}")
    print(f" INTEGRATION TEST — {port}")
    print(f"{'='*55}")

    client = AcuitySensorClient(port=port, sensor_id=0, timeout=3.0, debug=True)

    # ── TEST 1: Connect ─────────────────────────────────────
    print("\n[1] Connect to sensor...")
    result = client.connect()
    if result:
        ok("connect() returned True")
    else:
        fail("connect() returned False — aborting")
        return

    # ── TEST 2: Serial number ────────────────────────────────
    print("\n[2] Read serial number...")
    sn = client.read_serial_number()
    if sn and not is_error_response(sn):
        ok(f"Serial number: {sn}")
    else:
        fail(f"Serial number query failed: {sn}")

    # ── TEST 3: Firmware ─────────────────────────────────────
    print("\n[3] Read firmware version...")
    fw = client.read_firmware_version()
    if fw and not is_error_response(fw):
        ok(f"Firmware version: {fw}")
    else:
        fail(f"Firmware query failed: {fw}")

    # ── TEST 4: Single measurement ───────────────────────────
    print("\n[4] Single measurement...")
    response = client.get_single_measurement()
    if response and not is_error_response(response):
        raw = parse_distance_response(response)
        if raw is not None:
            mm = convert_0p1mm_to_unit(raw, Unit.MM)
            ok(f"Single measurement: {mm:.4f} mm  (raw={raw}, response={response})")
        else:
            fail(f"Could not parse response: {response}")
    else:
        fail(f"Single measurement failed: {response}")

    # ── TEST 5: Continuous (collect 5 samples) ───────────────
    print("\n[5] Continuous tracking (collecting 5 samples)...")
    start_resp = client.start_continuous_tracking()
    if start_resp and not is_error_response(start_resp):
        ok(f"Continuous started: {start_resp}")
    else:
        fail(f"Continuous start failed: {start_resp}")

    samples = []
    deadline = time.time() + 5.0
    while time.time() < deadline and len(samples) < 5:
        data = client.read_available_data(wait_time=0.1)
        if data:
            for token in data.split():
                raw = parse_distance_response(token)
                if raw is not None:
                    mm = convert_0p1mm_to_unit(raw, Unit.MM)
                    samples.append(mm)
                    print(f"    Sample {len(samples)}: {mm:.4f} mm")
                    if len(samples) >= 5:
                        break

    if len(samples) >= 5:
        ok(f"Collected {len(samples)} continuous samples")
    else:
        fail(f"Only collected {len(samples)}/5 samples in 5 seconds")

    # ── TEST 6: Stop continuous ──────────────────────────────
    print("\n[6] Stop continuous...")
    stop_resp = client.stop_measurement()
    if stop_resp is not None:
        ok(f"Stop response: {stop_resp}")
    else:
        fail("No response to stop command")

    # ── TEST 7: Disconnect ───────────────────────────────────
    print("\n[7] Disconnect...")
    client.disconnect()
    if not client.is_connected():
        ok("Disconnected cleanly")
    else:
        fail("Still shows connected after disconnect")

    # ── SUMMARY ─────────────────────────────────────────────
    total = passed + failed
    print(f"\n{'='*55}")
    print(f" RESULTS: {passed}/{total} passed  |  {failed} failed")
    print(f"{'='*55}")
    return failed == 0


if __name__ == "__main__":
    port = sys.argv[1] if len(sys.argv) > 1 else "COM4"
    success = run(port)
    sys.exit(0 if success else 1)
