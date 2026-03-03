# Acuity AS1100 Laser Sensor - Data Collection Application

This project provides both command-line and graphical user interface (GUI) tools for collecting, processing, and exporting distance measurement data from the Acuity AS1100 laser sensor.

## Features

- **Dual Interface**: Command-line script for testing/automation, or PySide6 GUI application for interactive data collection
- **Multiple Measurement Modes**: Continuous streaming or single-shot measurements
- **Flexible Interval Selection**: Choose from presets (100 Hz, 50 Hz, ..., 1 Hz) or custom frequencies
- **Sensor-Timed or Host-Throttled**: Leverage AS1100's hardware timing or throttle in software
- **Unit Conversion**: Output distance in mm, cm, m, km, feet, or inches
- **Timestamped Records**: Host system timestamp (ISO 8601) on every sample
- **CSV Export**: Structured data output with full metadata for post-processing
- **Live Data Display**: Real-time table view of collected samples during acquisition
- **Serial Configuration**: Auto-detect COM ports, select sensor ID, baud rate settings

## Installation

### Requirements
- Python 3.8+
- Windows, macOS, or Linux

### Dependencies
```bash
pip install -r requirements.txt
```

**requirements.txt** includes:
- `pyserial>=3.5` – Serial port communication
- `PySide6>=6.6.0` – GUI framework

## Usage

### Command-Line Script (CLI)

For testing, debugging, or automation:

```bash
python acuity_sensor.py
```

This opens an interactive menu with options to:
- Connect/disconnect from the sensor
- Trigger single measurements
- Start continuous tracking
- Read sensor info, version, error stack
- Send custom commands

**Menu Options:**
1. **Continuous Tracking** – Stream measurements at maximum rate or timed intervals
2. **Single Measurement** – Trigger one measurement on demand
3. **Stop/Clear** – Stop measurement mode
4. **Read Serial Number** – Query sensor ID (s#sn)
5. **Read Firmware Version** – Query firmware (s#sv)
6. **Raw Data Monitor** – Listen for incoming serial data

### GUI Application

For interactive data collection and export:

```bash
python -m app.main
```

**Main GUI Features:**

#### Connection Panel
- Port selector with auto-refresh
- Sensor ID configuration
- Connect/Disconnect button
- Real-time connection status

#### Measurement Settings
- **Mode**: `Continuous` or `Single`
  - *Continuous*: Stream measurements continuously until stopped
  - *Single*: Take one measurement per interval (scheduled singles)
- **Interval Mode**:
  - *Sensor-Timed*: Use AS1100's `s#h+ms` command for accurate hardware-timed cadence
  - *Host-Throttled*: Run at max speed, throttle sampling in application
- **Frequency**: Select from presets (100/50/20/10/5/2/1 Hz) or enter custom value (0.1–100 Hz)
- **Unit**: Choose output unit (mm, cm, m, km, ft, in)

#### Output Settings
- **Output Folder**: Select destination for CSV file (required before starting collection)
- Folder persists during session; can be changed anytime

#### Collection Control
- **Start Collection** – Begin measurement recording
- **Stop Collection** – End measurement and close CSV file
- Live sample count updates

#### Data Display
- **Live Table**: Shows timestamp, raw value, converted value, unit, mode, frequency, sensor ID
- **Status Log**: Real-time messages and error reporting
- **CSV Export**: Quick link to open the csv file in your default spreadsheet app

---

## CSV Export Format

Each collection generates a CSV file in the selected output folder named: `YYYYMMDD_HHMMSS.csv`

**Columns (Standard Schema):**
| Column | Description | Example |
|--------|-------------|---------|
| `timestamp_iso` | Host system timestamp (ISO 8601) | 2026-03-03T12:00:00.123456 |
| `epoch_ms` | Milliseconds since Unix epoch | 1740991200123 |
| `mode` | Measurement mode | continuous \| single |
| `interval_hz` | Sampling frequency (if applicable) | 10.0 |
| `raw_0.1mm` | Raw sensor value (0.1 mm units) | 2718 |
| `value` | Converted distance value | 271.8 |
| `unit` | Unit of converted value | mm |
| `sensor_id` | AS1100 sensor ID | 0 |
| `response` | Raw device response | g0g+00002718 |

**Example CSV output:**
```csv
timestamp_iso,epoch_ms,mode,interval_hz,raw_0.1mm,value,unit,sensor_id,response
2026-03-03T12:00:00.123456,1740991200123,continuous,10.0,2718,271.8,mm,0,g0g+00002718
2026-03-03T12:00:00.224567,1740991200224,continuous,10.0,2714,271.4,mm,0,g0g+00002714
2026-03-03T12:00:00.325678,1740991200325,continuous,10.0,2720,272.0,mm,0,g0g+00002720
```

---

## Measurement Modes Detail

### Continuous Mode
Continuously outputs measurements until stopped.

- **sensor-timed**: Sends `s#h+aaaaaaaa` command where `aaaaaaaa` is delay in milliseconds. Provides accurate, hardware-driven cadence.
- **host-throttled**: Runs maximum speed (≈100 Hz raw); application throttles reads to requested frequency.

### Single Mode (Scheduled Singles)
Sends individual `s#g` commands at selected interval until collection is stopped.

- Useful for power-sensitive applications or when measurement overhead matters
- Respects the selected frequency (10 Hz → one measurement every 100 ms)

---

## Unit Conversion Reference

Distance is measured in **0.1 mm units** by the AS1100.

**Conversion examples** (raw value 2718 = 271.8 mm):
| Unit | Factor | Result |
|------|--------|--------|
| mm | 0.1 | 271.8 |
| cm | 0.01 | 27.18 |
| m | 0.0001 | 0.2718 |
| km | 0.0000001 | 0.0002718 |
| ft | 0.000328084 | 0.8920 |
| in | 0.00393701 | 10.70 |

Conversion is performed at collection time and saved in the CSV.

---

## Serial Configuration

**Default Settings:**
- Port: COM4 (auto-detected)
- Baud Rate: 19200 baud
- Data Bits: 7
- Parity: Even
- Stop Bits: 1
- **Line Ending: CRLF (`\r\n`)** ← Critical for AS1100

**Changing Baud Rate (advanced):**
Modify `AcuitySensorClient` in [app/sensor/serial_client.py](app/sensor/serial_client.py) or use CLI menu option to reconfigure sensor via `s#br` command.

---

## Testing

Run unit tests for parsing, conversion, and CSV export:

```bash
python -m unittest tests.test_parsing
python -m unittest tests.test_conversion
python -m unittest tests.test_csv_exporter
```

---

## Troubleshooting

### No ports detected
- Verify sensor is powered and connected via USB/serial adapter
- Check Windows Device Manager or `ls /dev/tty*` on Linux/macOS
- Try `Refresh` button in GUI or re-run CLI

### Connection fails
- Confirm correct COM port is selected
- Verify sensor is not already open in another application
- Check baud rate matches sensor configuration (default 19200)

### No measurements received
- Ensure target is in measurement range (≈2 in. to 328 ft for natural targets)
- Verify adequate target reflectivity (dark surfaces may require closer proximity)
- Check sensor error stack via CLI menu option 7 → `s0re`
- See [manual.md](manual.md) Section 5.2 for error code meanings

### CSV file not created
- Verify output folder path is accessible and writable
- Check host disk space
- Review status log for I/O errors

---

## Hardware & Protocol Reference

See [manual.md](manual.md) for complete AS1100 specifications and command protocol.

**Key AS1100 commands used:**
- `s#g` – Single distance measurement
- `s#h` – Continuous tracking
- `s#h+ms` – Timed tracking at interval
- `s#c` – Stop/Clear
- `s#sn` – Read serial number
- `s#sv` – Read firmware version
- `s#re` – Read error stack

---

## Project Structure

```
.
├── app/                          # Main application package
│   ├── __init__.py
│   ├── main.py                   # GUI entry point
│   ├── domain/
│   │   ├── models.py             # Data models (MeasurementMode, SampleRecord, etc.)
│   │   └── conversion.py         # Unit conversion logic
│   ├── gui/
│   │   ├── main_window.py        # PySide6 main window UI
│   │   └── __init__.py
│   ├── sensor/
│   │   ├── serial_client.py      # AS1100 low-level serial client
│   │   ├── parsing.py            # Response parsing utilities
│   │   └── __init__.py
│   ├── io/
│   │   ├── csv_exporter.py       # CSV file export
│   │   └── __init__.py
│   └── workers/
│       ├── acquisition_worker.py # Background data collection thread
│       └── __init__.py
├── tests/                        # Unit tests
│   ├── test_parsing.py
│   ├── test_conversion.py
│   ├── test_csv_exporter.py
│   └── __init__.py
├── acuity_sensor.py              # Original CLI script
├── manual.md                     # AS1100 protocol documentation
├── requirements.txt
└── README.md
```

---

## License & Attribution

This project uses the Acuity AS1100 Accurate Distance Sensor. AS1100™ is a product of Schmitt Measurement Systems, Inc.

See [manual.md](manual.md) for the full user license and warranty information.

---

## Support

For sensor-specific questions, contact:
- **Acuity/Schmitt Measurement Systems, Inc.**
- 8000 NE 14th Place, Portland, OR 97211
- http://www.acuitylaser.com

For application bugs or feature requests, review the [manual.md](manual.md) protocol reference and check error codes in Section 5.2.

