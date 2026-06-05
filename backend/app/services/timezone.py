"""Timezone helpers for producing host-local timestamps."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta, timezone, tzinfo

from app.sensor.agent_client import get_agent_time_info
from app.sensor.provider import get_provider_mode


_CACHE_TTL_SECONDS = 300.0
_timezone_cache: tzinfo | None = None
_timezone_cache_expires_at = 0.0
_timezone_cache_lock = threading.Lock()


def _backend_local_timezone() -> tzinfo:
    """Return the backend process local timezone as an aware tzinfo."""
    return datetime.now().astimezone().tzinfo or timezone.utc


def _fixed_offset_timezone(offset_minutes: int, timezone_name: str | None = None) -> tzinfo:
    """Build a timezone from a UTC offset in minutes."""
    delta = timedelta(minutes=int(offset_minutes))
    if timezone_name:
        return timezone(delta, timezone_name)
    return timezone(delta)


def _format_utc_offset_label(offset_minutes: int) -> str:
    """Return a normalized UTC offset label such as UTC-04:00."""
    total_minutes = int(offset_minutes)
    sign = "+" if total_minutes >= 0 else "-"
    absolute_minutes = abs(total_minutes)
    hours, minutes = divmod(absolute_minutes, 60)
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def _resolve_host_timezone_uncached() -> tzinfo:
    """Resolve the host machine timezone, falling back to backend local time."""
    if get_provider_mode() != "agent":
        return _backend_local_timezone()

    try:
        payload = get_agent_time_info()
        offset_minutes = int(payload.get("utc_offset_minutes", 0))
        timezone_name = str(payload.get("timezone_name") or "").strip() or None
        return _fixed_offset_timezone(offset_minutes, timezone_name)
    except Exception:
        return _backend_local_timezone()


def get_host_timezone() -> tzinfo:
    """Return the effective host timezone with a short-lived cache."""
    if get_provider_mode() != "agent":
        return _backend_local_timezone()

    now_monotonic = time.monotonic()
    global _timezone_cache, _timezone_cache_expires_at

    with _timezone_cache_lock:
        if _timezone_cache is not None and now_monotonic < _timezone_cache_expires_at:
            return _timezone_cache

        _timezone_cache = _resolve_host_timezone_uncached()
        _timezone_cache_expires_at = now_monotonic + _CACHE_TTL_SECONDS
        return _timezone_cache


def now_in_host_timezone() -> datetime:
    """Return the current time using the resolved host timezone."""
    return datetime.now(get_host_timezone())


def from_epoch_in_host_timezone(epoch_seconds: float) -> datetime:
    """Convert an epoch timestamp to the resolved host timezone."""
    return datetime.fromtimestamp(epoch_seconds, tz=get_host_timezone())


def get_host_timezone_info() -> dict[str, str | int]:
    """Return display-friendly metadata about the effective host timezone."""
    now = now_in_host_timezone()
    offset = now.utcoffset()
    offset_minutes = int(offset.total_seconds() // 60) if offset is not None else 0
    timezone_name = now.tzname() or "local"
    return {
        "timestamp_timezone_name": timezone_name,
        "timestamp_utc_offset_minutes": offset_minutes,
        "timestamp_utc_offset_label": _format_utc_offset_label(offset_minutes),
    }


def format_host_datetime_for_filename(value: datetime | None = None) -> str:
    """Return a filesystem-safe host-local timestamp label for exports."""
    dt = value or now_in_host_timezone()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=get_host_timezone())
    else:
        dt = dt.astimezone(get_host_timezone())

    offset = dt.utcoffset()
    offset_minutes = int(offset.total_seconds() // 60) if offset is not None else 0
    offset_label = _format_utc_offset_label(offset_minutes).replace(":", "")
    return f"{dt.strftime('%Y%m%d_%H%M%S')}_{offset_label}"