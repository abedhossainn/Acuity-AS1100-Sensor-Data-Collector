"""Host sensor agent service for COM-port access outside containers."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
import threading
import uuid
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Reuse the backend serial implementation to keep command behavior consistent.
ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.sensor.serial_client import AcuitySensorClient  # noqa: E402


class ConnectionOpenRequest(BaseModel):
    port: str
    baudrate: int = 19200
    serial_profile: str = "7E1"
    timeout: float = 3.0
    sensor_id: int = 0
    debug: bool = False


class ConnectionResponse(BaseModel):
    connection_id: str
    port: str
    connected: bool


class MeasuringModeRequest(BaseModel):
    mode_code: int = Field(..., ge=0, le=4)


class TrackingStartRequest(BaseModel):
    interval_ms: Optional[int] = Field(default=None, ge=0, le=86400000)


app = FastAPI(title="AS1100 Host Sensor Agent", version="1.0.0")

_connections: Dict[str, AcuitySensorClient] = {}
_connections_lock = threading.Lock()


def _get_client(connection_id: str) -> AcuitySensorClient:
    with _connections_lock:
        client = _connections.get(connection_id)
    if not client:
        raise HTTPException(status_code=404, detail="Connection not found")
    return client


@app.get("/health")
def health() -> dict:
    with _connections_lock:
        open_count = len(_connections)
    return {"status": "ok", "open_connections": open_count}


@app.get("/time-info")
def time_info() -> dict:
    now = datetime.now().astimezone()
    offset = now.utcoffset()
    offset_minutes = int(offset.total_seconds() // 60) if offset is not None else 0
    return {
        "host_time_iso": now.isoformat(),
        "timezone_name": now.tzname() or "local",
        "utc_offset_minutes": offset_minutes,
    }


@app.get("/ports")
def list_ports() -> list[dict]:
    return AcuitySensorClient.list_ports_detailed()


@app.post("/connections", response_model=ConnectionResponse)
def open_connection(req: ConnectionOpenRequest):
    client = AcuitySensorClient(
        port=req.port,
        baudrate=req.baudrate,
        serial_profile=req.serial_profile,
        timeout=req.timeout,
        sensor_id=req.sensor_id,
        debug=req.debug,
    )

    if not client.connect():
        detail = client.last_connect_error or f"Failed to connect sensor on {req.port}"
        raise HTTPException(
            status_code=400,
            detail=(
                f"Failed to connect sensor on {req.port} at {req.baudrate} baud "
                f"({req.serial_profile}). {detail}"
            ),
        )

    connection_id = uuid.uuid4().hex
    with _connections_lock:
        _connections[connection_id] = client

    return ConnectionResponse(connection_id=connection_id, port=req.port, connected=True)


@app.get("/connections/{connection_id}")
def get_connection(connection_id: str) -> dict:
    client = _get_client(connection_id)
    return {"connection_id": connection_id, "connected": client.is_connected(), "port": client.port}


@app.delete("/connections/{connection_id}")
def close_connection(connection_id: str) -> dict:
    with _connections_lock:
        client = _connections.pop(connection_id, None)

    if not client:
        raise HTTPException(status_code=404, detail="Connection not found")

    try:
        client.disconnect()
    except Exception:
        pass

    return {"connection_id": connection_id, "closed": True}


@app.post("/connections/{connection_id}/laser-on")
def laser_on(connection_id: str) -> dict:
    client = _get_client(connection_id)
    response = client.laser_on()
    return {"connection_id": connection_id, "response": response}


@app.post("/connections/{connection_id}/laser-off")
def laser_off(connection_id: str) -> dict:
    client = _get_client(connection_id)
    response = client.laser_off()
    return {"connection_id": connection_id, "response": response}


@app.post("/connections/{connection_id}/measurement")
def measurement(connection_id: str) -> dict:
    client = _get_client(connection_id)
    response = client.get_measurement()
    return {"connection_id": connection_id, "response": response}


@app.post("/connections/{connection_id}/single-measurement")
def single_measurement(connection_id: str) -> dict:
    """Backward-compatible alias for /connections/{connection_id}/measurement."""
    return measurement(connection_id)


@app.post("/connections/{connection_id}/measuring-mode")
def set_measuring_mode(connection_id: str, req: MeasuringModeRequest) -> dict:
    client = _get_client(connection_id)
    ok = client.set_measuring_mode(req.mode_code)
    if not ok:
        raise HTTPException(status_code=400, detail="Failed to set measuring mode")
    return {"connection_id": connection_id, "ok": True, "mode_code": req.mode_code}


@app.post("/connections/{connection_id}/tracking/start")
def start_tracking(connection_id: str, req: TrackingStartRequest | None = None) -> dict:
    client = _get_client(connection_id)
    interval_ms = req.interval_ms if req else None
    if interval_ms is None:
        response = client.start_continuous_tracking()
    else:
        response = client.start_timed_tracking(interval_ms)
    return {"connection_id": connection_id, "response": response}


@app.post("/connections/{connection_id}/tracking/stop")
def stop_tracking(connection_id: str) -> dict:
    client = _get_client(connection_id)
    response = client.stop_measurement()
    return {"connection_id": connection_id, "response": response}


@app.get("/connections/{connection_id}/tracking/chunk")
def read_tracking_chunk(connection_id: str) -> dict:
    client = _get_client(connection_id)
    chunk = client.read_stream_chunk()
    return {"connection_id": connection_id, "chunk": chunk}


@app.on_event("shutdown")
def on_shutdown() -> None:
    with _connections_lock:
        connection_ids = list(_connections.keys())

    for connection_id in connection_ids:
        with _connections_lock:
            client: Optional[AcuitySensorClient] = _connections.pop(connection_id, None)
        if client:
            try:
                client.disconnect()
            except Exception:
                pass
