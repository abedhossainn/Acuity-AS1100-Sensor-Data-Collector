"""Host sensor-agent client used by backend when direct serial access is unavailable."""

from __future__ import annotations

import os
from typing import List, Optional

import httpx


def get_agent_base_url() -> str:
    """Resolve agent base URL from environment."""
    return os.getenv("AGENT_BASE_URL", "http://host.docker.internal:8010").rstrip("/")


def get_agent_time_info() -> dict:
    """Return current host time metadata from the host agent."""
    response = httpx.get(f"{get_agent_base_url()}/time-info", timeout=5.0)
    response.raise_for_status()
    return response.json() if response.content else {}


class AgentSensorClient:
    """AS1100 client implementation that proxies commands to the host sensor agent."""

    def __init__(
        self,
        port: str,
        baudrate: int = 19200,
        serial_profile: str = "7E1",
        timeout: float = 3.0,
        sensor_id: int = 0,
        debug: bool = False,
    ):
        self.port = port
        self.baudrate = baudrate
        self.serial_profile = str(serial_profile).strip().upper() or "7E1"
        self.timeout = timeout
        self.sensor_id = int(sensor_id)
        self.debug = debug
        self.connection_id: Optional[str] = None
        self.last_connect_error: str = ""

    def _request(self, method: str, path: str, json_body: Optional[dict] = None) -> dict:
        url = f"{get_agent_base_url()}{path}"
        response = httpx.request(method, url, json=json_body, timeout=max(5.0, self.timeout + 2.0))
        response.raise_for_status()
        return response.json() if response.content else {}

    def connect(self) -> bool:
        self.last_connect_error = ""
        try:
            payload = {
                "port": self.port,
                "baudrate": self.baudrate,
                "serial_profile": self.serial_profile,
                "timeout": self.timeout,
                "sensor_id": self.sensor_id,
                "debug": self.debug,
            }
            result = self._request("POST", "/connections", payload)
            self.connection_id = result.get("connection_id")
            return bool(self.connection_id)
        except httpx.HTTPStatusError as e:
            detail = ""
            try:
                body = e.response.json() if e.response is not None else {}
                detail = str(body.get("detail") or "")
            except Exception:
                detail = ""
            self.last_connect_error = detail or str(e)
            self.connection_id = None
            return False
        except Exception as e:
            self.last_connect_error = str(e)
            self.connection_id = None
            return False

    def disconnect(self) -> None:
        if not self.connection_id:
            return
        try:
            self._request("DELETE", f"/connections/{self.connection_id}")
        except Exception:
            pass
        finally:
            self.connection_id = None

    def is_connected(self) -> bool:
        return bool(self.connection_id)

    def laser_on(self) -> Optional[str]:
        if not self.connection_id:
            return None
        try:
            result = self._request("POST", f"/connections/{self.connection_id}/laser-on")
            return result.get("response")
        except Exception:
            return None

    def laser_off(self) -> Optional[str]:
        if not self.connection_id:
            return None
        try:
            result = self._request("POST", f"/connections/{self.connection_id}/laser-off")
            return result.get("response")
        except Exception:
            return None

    def set_measuring_mode(self, mode_code: int) -> bool:
        if not self.connection_id:
            return False
        try:
            self._request("POST", f"/connections/{self.connection_id}/measuring-mode", {"mode_code": int(mode_code)})
            return True
        except Exception:
            return False

    def start_continuous_tracking(self) -> Optional[str]:
        if not self.connection_id:
            return None
        try:
            result = self._request("POST", f"/connections/{self.connection_id}/tracking/start")
            return result.get("response")
        except Exception:
            return None

    def start_timed_tracking(self, interval_ms: int) -> Optional[str]:
        if not self.connection_id:
            return None
        try:
            result = self._request(
                "POST",
                f"/connections/{self.connection_id}/tracking/start",
                {"interval_ms": int(interval_ms)},
            )
            return result.get("response")
        except Exception:
            return None

    def stop_measurement(self) -> Optional[str]:
        if not self.connection_id:
            return None
        try:
            result = self._request("POST", f"/connections/{self.connection_id}/tracking/stop")
            return result.get("response")
        except Exception:
            return None

    def read_stream_chunk(self) -> Optional[str]:
        if not self.connection_id:
            return None
        try:
            result = self._request("GET", f"/connections/{self.connection_id}/tracking/chunk")
            return result.get("chunk")
        except Exception:
            return None

    def get_measurement(self) -> Optional[str]:
        if not self.connection_id:
            return None
        try:
            result = self._request("POST", f"/connections/{self.connection_id}/measurement")
            return result.get("response")
        except Exception:
            # Backward compatibility with older host-agent endpoint name.
            try:
                result = self._request("POST", f"/connections/{self.connection_id}/single-measurement")
                return result.get("response")
            except Exception:
                return None

    def get_single_measurement(self) -> Optional[str]:
        """Backward-compatible alias for get_measurement()."""
        return self.get_measurement()

    @staticmethod
    def list_ports_detailed() -> List[dict]:
        response = httpx.get(f"{get_agent_base_url()}/ports", timeout=5.0)
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list):
            return payload
        return payload.get("ports", [])

    @staticmethod
    def get_port_device(port_string: str) -> str:
        if " - " in port_string:
            return port_string.split(" - ")[0].strip()
        return port_string.strip()
