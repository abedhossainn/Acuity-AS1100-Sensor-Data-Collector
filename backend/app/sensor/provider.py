"""Sensor provider selection utilities (direct serial vs host agent)."""

from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import List
import httpx

from app.sensor.agent_client import AgentSensorClient, get_agent_base_url
from app.sensor.serial_client import AcuitySensorClient


def _configured_provider() -> str:
    return os.getenv("SENSOR_PROVIDER", "auto").strip().lower()


def _is_in_container() -> bool:
    return Path("/.dockerenv").exists() or os.getenv("KUBERNETES_SERVICE_HOST") is not None


def get_provider_mode() -> str:
    """Return resolved provider mode: 'direct' or 'agent'."""
    configured = _configured_provider()
    if configured in {"direct", "agent"}:
        return configured

    # auto mode: containerized Linux backends should use host agent by default.
    if _is_in_container() and platform.system().lower() == "linux":
        return "agent"
    return "direct"


def get_provider_note() -> str:
    mode = get_provider_mode()
    if mode == "agent":
        return f"Using host sensor agent ({get_agent_base_url()})"
    return "Using direct serial provider"


def list_ports_detailed() -> List[dict]:
    mode = get_provider_mode()
    configured = _configured_provider()

    if mode == "agent":
        try:
            return AgentSensorClient.list_ports_detailed()
        except Exception:
            if configured == "auto":
                return AcuitySensorClient.list_ports_detailed()
            raise

    return AcuitySensorClient.list_ports_detailed()


def create_sensor_client(
    port: str,
    sensor_id: int = 0,
    debug: bool = False,
    baudrate: int = 19200,
    serial_profile: str = "7E1",
    timeout: float = 3.0,
):
    mode = get_provider_mode()
    if mode == "agent":
        return AgentSensorClient(
            port=port,
            sensor_id=sensor_id,
            debug=debug,
            baudrate=baudrate,
            serial_profile=serial_profile,
            timeout=timeout,
        )
    return AcuitySensorClient(
        port=port,
        sensor_id=sensor_id,
        debug=debug,
        baudrate=baudrate,
        serial_profile=serial_profile,
        timeout=timeout,
    )


def check_agent_health(timeout_seconds: float = 1.5) -> tuple[bool, str]:
    """Return (reachable, message) for the configured host sensor agent."""
    url = f"{get_agent_base_url()}/health"
    try:
        response = httpx.get(url, timeout=timeout_seconds)
        response.raise_for_status()
        payload = response.json() if response.content else {}
        if payload.get("status") == "ok":
            return True, "Agent reachable"
        return False, "Agent health endpoint returned unexpected payload"
    except Exception as e:
        return False, str(e)
