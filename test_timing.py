"""Validate 5 Hz sample timing accuracy with new polling read_response."""
import time
from app.sensor.serial_client import AcuitySensorClient

c = AcuitySensorClient(port='COM4', sensor_id=0, timeout=3.0)
if not c.connect():
    raise SystemExit('connect failed')
print('Connected')

interval = 1.0 / 5   # 5 Hz target
sample_timeout = max(interval * 0.9, 2.0)
read_times = []
t_test_start = time.perf_counter()

for i in range(10):
    t0 = time.perf_counter()
    c.clear_input_buffer()
    c.send_command(c._cmd('g'))
    resp = c.read_response(wait_time=sample_timeout)
    elapsed = time.perf_counter() - t0
    read_times.append(elapsed)
    remaining = interval - elapsed
    if remaining > 0:
        time.sleep(remaining)

total = time.perf_counter() - t_test_start
c.disconnect()

print(f"\n10 samples @ 5 Hz target:")
print(f"  Total wall time : {total:.3f}s  (expected ~2.000s)")
print(f"  Achieved rate   : {10/total:.2f} Hz")
print(f"  Avg interval    : {total/10*1000:.1f} ms  (target 200 ms)")
print(f"  Per-sample read : {[f'{s*1000:.0f}ms' for s in read_times]}")
print(f"  Max read time   : {max(read_times)*1000:.0f} ms")
print(f"  Min read time   : {min(read_times)*1000:.0f} ms")
