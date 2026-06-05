"""Sensor collection capability constraints and helper utilities."""

from __future__ import annotations

from typing import List

SUPPORTED_BAUD_RATES: List[int] = [9600, 19200, 115200]
SUPPORTED_SERIAL_PROFILES: List[str] = ["7E1", "8N1"]

# Conservative limits aligned with AS1100 documentation guidance:
# - 115200 is required for 100 Hz operation.
# - Lower baud rates are intentionally capped for stability.
BAUD_MAX_HZ: dict[int, float] = {
    9600: 10.0,
    19200: 20.0,
    115200: 100.0,
}

MEASURING_MODE_MAX_HZ: dict[str, float] = {
    "normal": 20.0,
    "fast": 100.0,
    "precise": 10.0,
    "timed": 100.0,
    "moving_target": 100.0,
}

FREQUENCY_PRESETS_HZ: List[float] = [1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0]


def get_baud_max_hz(baud_rate: int) -> float:
    return BAUD_MAX_HZ.get(int(baud_rate), BAUD_MAX_HZ[19200])


def get_measuring_mode_max_hz(mode: str) -> float:
    return MEASURING_MODE_MAX_HZ.get(str(mode), 100.0)


def get_effective_max_hz(baud_rate: int, mode: str) -> float:
    return min(get_baud_max_hz(baud_rate), get_measuring_mode_max_hz(mode))


def get_supported_frequency_presets(baud_rate: int, mode: str) -> List[float]:
    limit = get_effective_max_hz(baud_rate, mode)
    return [hz for hz in FREQUENCY_PRESETS_HZ if hz <= limit]
