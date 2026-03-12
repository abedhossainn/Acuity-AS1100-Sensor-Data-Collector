"""
Timing test for the new s0h streaming + host-clock decimation approach.
"""
import time
from app.sensor.serial_client import AcuitySensorClient
from app.sensor.parsing import parse_distance_response, is_error_response

N_SAMPLES = 10
TARGET_HZ = 5
interval = 1.0 / TARGET_HZ

c = AcuitySensorClient(port='COM4', sensor_id=0, timeout=3.0)
if not c.connect():
    print('Cannot connect'); exit(1)
print('Connected')

# Start continuous streaming
c.clear_input_buffer()
c.send_command(c._cmd('h'))
c.read_response(wait_time=1.0)  # consume ACK

samples = []
measurements_received = 0
line_buf = ''
next_emit = time.perf_counter() + interval

while len(samples) < N_SAMPLES:
    chunk = c.read_stream_chunk()
    if chunk:
        line_buf += chunk
        while '\n' in line_buf:
            line, line_buf = line_buf.split('\n', 1)
            line = line.strip()
            if line and not is_error_response(line):
                raw = parse_distance_response(line)
                if raw is not None:
                    measurements_received += 1

    now = time.perf_counter()
    if now >= next_emit:
        samples.append(now)
        next_emit += interval
        if time.perf_counter() > next_emit + interval:
            next_emit = time.perf_counter() + interval
    time.sleep(0.001)

c.stop_measurement()
c.disconnect()

total = samples[-1] - samples[0]
gaps = [samples[i+1]-samples[i] for i in range(len(samples)-1)]
print(f'\n10 samples @ {TARGET_HZ} Hz target:')
print(f'  Total wall time    : {total:.3f}s  (expected ~{(N_SAMPLES-1)/TARGET_HZ:.3f}s)')
print(f'  Achieved rate      : {(N_SAMPLES-1)/total:.2f} Hz')
print(f'  Avg interval       : {1000*sum(gaps)/len(gaps):.1f} ms  (target {1000/TARGET_HZ:.0f} ms)')
print(f'  Sensor measurements: {measurements_received} received during test')
print(f'  Per-gap (ms)       : {[f"{g*1000:.1f}" for g in gaps]}')
print(f'  Max gap : {max(gaps)*1000:.1f} ms   Min gap : {min(gaps)*1000:.1f} ms')
