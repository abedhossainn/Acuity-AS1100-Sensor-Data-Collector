"""FastAPI application entry point."""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path
import asyncio
import time
import os
import platform
import logging
import re
from datetime import datetime
from io import StringIO
import csv
import shutil
from io import BytesIO
import zipfile

from app.models.schemas import (
    SessionConfig,
    SessionStatus,
    SessionStartResponse,
    ConnectionInfo,
    RateProbeRequest,
    ConnectionDoctorRequest,
    ConnectionDoctorResponse,
)
from app.services.session import SessionManager
from app.api.routes import router as api_router
from app.sensor.agent_client import get_agent_base_url
from app.sensor.provider import (
    check_agent_health,
    create_sensor_client,
    get_provider_mode,
    get_provider_note,
    list_ports_detailed,
)
from app.sensor.parsing import parse_distance_response
from app.domain.conversion import convert_0p1mm_to_unit
from app.domain.capabilities import (
    BAUD_MAX_HZ,
    FREQUENCY_PRESETS_HZ,
    MEASURING_MODE_MAX_HZ,
    SUPPORTED_BAUD_RATES,
    SUPPORTED_SERIAL_PROFILES,
    get_effective_max_hz,
)
from app.services.timezone import (
    format_host_datetime_for_filename,
    from_epoch_in_host_timezone,
    get_host_timezone_info,
    now_in_host_timezone,
)

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# Global session manager
session_manager: SessionManager = None
active_websockets: dict = {}
session_tasks: dict[str, asyncio.Task] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    global session_manager
    configured_dir = os.getenv("AS1100_DATA_DIR")
    if configured_dir:
        data_dir = Path(configured_dir)
    elif Path("/data").exists():
        data_dir = Path("/data")
    else:
        data_dir = Path.cwd() / "data_dir"

    session_manager = SessionManager(data_dir=data_dir)
    logger.info(f"CSV persistence directory: {session_manager.data_dir}")

    if get_provider_mode() == "agent":
        reachable, reason = check_agent_health()
        if reachable:
            logger.info(f"Host sensor agent reachable at {get_agent_base_url()}")
        else:
            logger.warning(
                f"Host sensor agent is not reachable at {get_agent_base_url()}: {reason}. "
                "Session start will be blocked until agent is online."
            )
    yield

    # Cleanup on shutdown
    for session_id in list(session_manager.sessions.keys()):
        session_manager.stop_session(session_id)
        session_manager.close_persistence(session_id)

    for task in list(session_tasks.values()):
        task.cancel()


app = FastAPI(
    title="AS1100 Sensor Data Collector",
    description="Web-based sensor data collection API",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
MEASURING_MODE_CODE = {
    "normal": 0,
    "fast": 1,
    "precise": 2,
    "timed": 3,
    "moving_target": 4,
}


def _validate_session_id(session_id: str) -> None:
    if not SESSION_ID_PATTERN.fullmatch(session_id):
        raise HTTPException(status_code=400, detail="Invalid session id")


def _session_dir(session_id: str) -> Path:
    return session_manager.data_dir / session_id


def _list_session_csv_files(session_id: str) -> list[Path]:
    folder = _session_dir(session_id)
    if not folder.exists() or not folder.is_dir():
        return []
    return sorted(folder.glob("session_*.csv"))


def _merge_session_csv(files: list[Path]) -> str:
    merged_lines: list[str] = []
    for index, csv_file in enumerate(files):
        with open(csv_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if index == 0:
            merged_lines.extend(lines)
        elif len(lines) > 1:
            merged_lines.extend(lines[1:])
    return "".join(merged_lines)


def _count_csv_data_rows(files: list[Path]) -> int:
    """Count CSV data rows across part files (excluding per-file headers)."""
    total = 0
    for csv_file in files:
        with open(csv_file, "r", encoding="utf-8") as f:
            line_count = sum(1 for _ in f)
        total += max(0, line_count - 1)
    return total


def _build_export_filename(
    session_id: str,
    extension: str,
    reference_dt: datetime | None = None,
    suffix: str | None = None,
) -> str:
    """Build a host-local export filename for CSV/ZIP downloads."""
    timestamp_label = format_host_datetime_for_filename(reference_dt)
    parts = [f"session_{session_id}", timestamp_label]
    if suffix:
        parts.append(suffix)
    return f"{'_'.join(parts)}.{extension}"


def _session_reference_datetime(session) -> datetime:
    """Best-effort host-local reference time for export filenames."""
    csv_files = session_manager.get_csv_files(session.session_id)
    if csv_files:
        last_updated_epoch = max(f.stat().st_mtime for f in csv_files)
        return from_epoch_in_host_timezone(last_updated_epoch)

    if session.samples:
        latest_timestamp = session.samples[-1].get("timestamp_iso")
        if latest_timestamp:
            try:
                return datetime.fromisoformat(latest_timestamp)
            except ValueError:
                pass

    return now_in_host_timezone()


def _build_connection_failure_detail(
    port: str,
    sensor_id: int,
    requested_baud: int,
    requested_profile: str,
    initial_error: str = "",
) -> str:
    """Return actionable diagnostics when a sensor connection attempt fails."""
    normalized_profile = str(requested_profile).strip().upper() or "7E1"
    normalized_error = str(initial_error or "").strip()

    # Fast path for host-agent outages: this is not a baud issue.
    if get_provider_mode() == "agent":
        reachable, reason = check_agent_health()
        if not reachable:
            return (
                f"Failed to connect sensor on {port} at {requested_baud} baud ({normalized_profile}). "
                f"Host sensor agent is unreachable ({reason})."
            )

    low_error = normalized_error.lower()
    if "access is denied" in low_error or "permissionerror" in low_error:
        return (
            f"Failed to connect sensor on {port} at {requested_baud} baud ({normalized_profile}). "
            "The serial port is busy or access is denied (possibly open in another app)."
        )

    if "could not open port" in low_error:
        return (
            f"Failed to connect sensor on {port} at {requested_baud} baud ({normalized_profile}). "
            f"Serial open error: {normalized_error}"
        )

    # Probe supported baud/profile combinations to identify likely serial mismatch.
    probe_combinations: list[tuple[int, str]] = [(requested_baud, normalized_profile)]
    for profile in SUPPORTED_SERIAL_PROFILES:
        for baud in SUPPORTED_BAUD_RATES:
            combo = (baud, profile)
            if combo not in probe_combinations:
                probe_combinations.append(combo)

    for baud, profile in probe_combinations:
        candidate = create_sensor_client(
            port=port,
            sensor_id=sensor_id,
            debug=False,
            baudrate=baud,
            serial_profile=profile,
            timeout=0.8,
        )
        try:
            if candidate.connect():
                if baud != requested_baud or profile != normalized_profile:
                    return (
                        f"Failed to connect sensor on {port} at {requested_baud} baud ({normalized_profile}). "
                        f"Sensor responded at {baud} baud ({profile}), which suggests a serial settings mismatch. "
                        f"Select {baud}/{profile} in the app or reconfigure sensor serial settings (s#br) and save (s#s)."
                    )
                break
        except Exception:
            pass
        finally:
            try:
                candidate.disconnect()
            except Exception:
                pass

    return (
        f"Failed to connect sensor on {port} at {requested_baud} baud ({normalized_profile}). "
        "No valid sensor response was received. Check sensor power/cabling, COM port selection, and serial settings."
    )


def _run_connection_doctor(req: ConnectionDoctorRequest) -> ConnectionDoctorResponse:
    """Probe serial combinations and return a best-fit recommendation."""
    attempted: list[dict] = []
    requested_baud = int(req.current_baud_rate)
    requested_profile = req.current_serial_profile.value

    probe_combinations: list[tuple[int, str]] = [(requested_baud, requested_profile)]
    for profile in SUPPORTED_SERIAL_PROFILES:
        for baud in SUPPORTED_BAUD_RATES:
            combo = (baud, profile)
            if combo not in probe_combinations:
                probe_combinations.append(combo)

    recommended_baud: int | None = None
    recommended_profile: str | None = None

    for baud, profile in probe_combinations:
        client = create_sensor_client(
            port=req.port,
            sensor_id=req.sensor_id,
            debug=False,
            baudrate=baud,
            serial_profile=profile,
            timeout=0.8,
        )

        success = False
        detail: str | None = None
        try:
            success = bool(client.connect())
            if success:
                detail = "Sensor responded"
                attempted.append(
                    {
                        "baud_rate": baud,
                        "serial_profile": profile,
                        "success": True,
                        "detail": detail,
                    }
                )
                recommended_baud = baud
                recommended_profile = profile
                break
            detail = getattr(client, "last_connect_error", "") or None
        except Exception as e:
            detail = str(e)
        finally:
            try:
                client.disconnect()
            except Exception:
                pass

        attempted.append(
            {
                "baud_rate": baud,
                "serial_profile": profile,
                "success": False,
                "detail": detail,
            }
        )

    if recommended_baud is not None and recommended_profile is not None:
        if recommended_baud == requested_baud and recommended_profile == requested_profile:
            summary = (
                f"Connection settings are valid for {req.port}: {recommended_baud} baud ({recommended_profile})."
            )
        else:
            summary = (
                f"Recommended serial settings for {req.port}: "
                f"{recommended_baud} baud ({recommended_profile})."
            )
    else:
        first_error = attempted[0].get("detail") if attempted else ""
        summary = _build_connection_failure_detail(
            port=req.port,
            sensor_id=req.sensor_id,
            requested_baud=requested_baud,
            requested_profile=requested_profile,
            initial_error=first_error or "",
        )

    return ConnectionDoctorResponse(
        port=req.port,
        sensor_id=req.sensor_id,
        attempted=attempted,
        recommended_baud_rate=recommended_baud,
        recommended_serial_profile=recommended_profile,
        summary=summary,
    )


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/api/connections", response_model=list[ConnectionInfo])
async def list_connections():
    """List available serial ports."""
    try:
        ports = list_ports_detailed()
        return [
            ConnectionInfo(port=p["port"], description=p.get("description"))
            for p in ports
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/system-info")
async def system_info():
    """Return runtime diagnostics useful for serial-port troubleshooting."""
    ports: list[dict] = []
    in_container = Path("/.dockerenv").exists() or os.getenv("KUBERNETES_SERVICE_HOST") is not None
    system_name = platform.system().lower()
    provider_mode = get_provider_mode()
    agent_reachable = None
    agent_reason = ""

    if provider_mode == "agent":
        agent_reachable, agent_reason = check_agent_health()

    try:
        ports = list_ports_detailed()
    except Exception as e:
        if provider_mode == "agent":
            agent_reachable = False
            agent_reason = str(e)
        else:
            raise

    serial_note = ""
    if provider_mode == "agent":
        if agent_reachable:
            serial_note = f"Sensor provider is host-agent at {get_agent_base_url()}"
        else:
            serial_note = (
                f"Sensor provider is host-agent at {get_agent_base_url()}, but it is currently unreachable: "
                f"{agent_reason}"
            )
    elif in_container and system_name == "linux":
        serial_note = (
            "Linux containers on Docker Desktop for Windows cannot directly read host COM ports. "
            "Set SENSOR_PROVIDER=agent and run host sensor agent for COM access."
        )

    return {
        "os": platform.platform(),
        "in_container": in_container,
        "sensor_provider": provider_mode,
        "provider_note": get_provider_note(),
        "agent_reachable": agent_reachable,
        "agent_reason": agent_reason,
        "port_count": len(ports),
        "ports": ports,
        "serial_note": serial_note,
        **get_host_timezone_info(),
    }


@app.get("/api/capabilities")
async def capabilities():
    """Return frontend-consumable sensor capability limits."""
    return {
        "supported_baud_rates": SUPPORTED_BAUD_RATES,
        "supported_serial_profiles": SUPPORTED_SERIAL_PROFILES,
        "baud_max_hz": BAUD_MAX_HZ,
        "measuring_mode_max_hz": MEASURING_MODE_MAX_HZ,
        "frequency_presets_hz": FREQUENCY_PRESETS_HZ,
    }


@app.get("/api/storage-status")
async def storage_status():
    """Return storage durability and writable path diagnostics."""
    path = session_manager.data_dir
    writable = os.access(path, os.W_OK)
    total, used, free = shutil.disk_usage(path)

    return {
        "data_dir": str(path),
        "exists": path.exists(),
        "writable": writable,
        "persistence_mode": session_manager.persistence_mode,
        "durable_writes": session_manager.durable_writes,
        "csv_fsync_interval_rows": session_manager.fsync_interval_rows,
        "sqlite_commit_interval_rows": session_manager.sqlite_commit_interval_rows,
        "disk_total_bytes": total,
        "disk_used_bytes": used,
        "disk_free_bytes": free,
    }


@app.post("/api/connections/doctor", response_model=ConnectionDoctorResponse)
async def diagnose_connection(req: ConnectionDoctorRequest):
    """Diagnose best serial settings for a selected port."""
    if not req.port.strip():
        raise HTTPException(status_code=400, detail="port is required")

    try:
        return _run_connection_doctor(req)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/capabilities/probe-rate")
async def probe_rate_limits(req: RateProbeRequest):
    """Probe achievable sample rates on the selected sensor configuration."""
    static_max_hz = get_effective_max_hz(req.baud_rate, req.measuring_mode.value)
    candidates = [hz for hz in FREQUENCY_PRESETS_HZ if hz <= static_max_hz]
    if not candidates:
        raise HTTPException(status_code=400, detail="No probe candidates available for selected settings")

    mode_code = MEASURING_MODE_CODE.get(req.measuring_mode.value, 0)
    timeout = max(0.2, min(0.8, (1.0 / max(candidates)) * 2.0))
    client = create_sensor_client(
        port=req.port,
        sensor_id=req.sensor_id,
        debug=False,
        baudrate=req.baud_rate,
        serial_profile=req.serial_profile.value,
        timeout=timeout,
    )

    if not client.connect():
        detail = _build_connection_failure_detail(
            port=req.port,
            sensor_id=req.sensor_id,
            requested_baud=req.baud_rate,
            requested_profile=req.serial_profile.value,
            initial_error=getattr(client, "last_connect_error", ""),
        )
        raise HTTPException(status_code=400, detail=detail)

    results: list[dict] = []
    try:
        if hasattr(client, "set_measuring_mode"):
            client.set_measuring_mode(mode_code)

        for target_hz in candidates:
            interval_ms = max(1, int(round(1000.0 / target_hz)))
            start_error: str | None = None
            start_ack_missing = False

            try:
                if hasattr(client, "start_timed_tracking"):
                    start_response = client.start_timed_tracking(interval_ms)
                elif hasattr(client, "start_continuous_tracking"):
                    start_response = client.start_continuous_tracking()
                else:
                    start_response = None

                if start_response is None:
                    start_ack_missing = True
            except Exception as e:
                start_error = str(e)

            if start_error is not None:
                results.append(
                    {
                        "target_hz": target_hz,
                        "achieved_hz": 0.0,
                        "samples": 0,
                        "duration_seconds": req.duration_seconds,
                        "stable": False,
                        "note": f"Tracking start exception: {start_error}",
                    }
                )
                if hasattr(client, "stop_measurement"):
                    client.stop_measurement()
                await asyncio.sleep(0.05)
                continue

            buffer = ""
            count = 0
            start_t = time.perf_counter()
            end_t = start_t + req.duration_seconds

            while time.perf_counter() < end_t:
                try:
                    chunk = client.read_stream_chunk() if hasattr(client, "read_stream_chunk") else None
                except Exception:
                    chunk = None

                if chunk:
                    buffer += chunk
                    lines = buffer.split("\n")
                    buffer = lines.pop() if lines else ""
                    for raw_line in lines:
                        line = raw_line.strip()
                        if not line:
                            continue
                        if parse_distance_response(line) is not None:
                            count += 1

                await asyncio.sleep(0.001)

            elapsed = max(1e-6, time.perf_counter() - start_t)
            achieved_hz = count / elapsed
            stable = achieved_hz >= (0.80 * target_hz)
            note = None
            if count == 0:
                note = "No measurement samples received during probe window"
            elif start_ack_missing:
                note = "Tracking started without immediate ACK response"

            results.append(
                {
                    "target_hz": target_hz,
                    "achieved_hz": round(achieved_hz, 2),
                    "samples": count,
                    "duration_seconds": round(elapsed, 3),
                    "stable": stable,
                    "note": note,
                }
            )

            if hasattr(client, "stop_measurement"):
                client.stop_measurement()
            await asyncio.sleep(0.05)

        stable_rates = [r["target_hz"] for r in results if r.get("stable")]
        recommended = max(stable_rates) if stable_rates else min(candidates)

        return {
            "port": req.port,
            "baud_rate": req.baud_rate,
            "measuring_mode": req.measuring_mode.value,
            "duration_seconds": req.duration_seconds,
            "static_max_hz": static_max_hz,
            "recommended_max_hz": recommended,
            "results": results,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            if hasattr(client, "stop_measurement"):
                client.stop_measurement()
            client.disconnect()
        except Exception:
            pass


@app.post("/api/sessions", response_model=dict)
async def create_session(config: SessionConfig):
    """Create a new data collection session."""
    try:
        session = session_manager.create_session(config)
        return {
            "session_id": session.session_id,
            "message": f"Session created with {len(session.active_connections)} connection(s)",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/sessions/{session_id}", response_model=SessionStatus)
async def get_session_status(session_id: str):
    """Get current session status."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionStatus(
        session_id=session_id,
        is_running=session.is_running,
        sample_count=session.sample_count,
        start_time=session.start_time,
        connections_status=session.connections_status,
    )


@app.post("/api/sessions/{session_id}/start", response_model=SessionStartResponse)
async def start_session(session_id: str):
    """Start data collection (returns 5-second boundary)."""
    logger.debug(f"Start session request for {session_id}")
    
    session = session_manager.get_session(session_id)
    if not session:
        logger.error(f"Start session: session {session_id} not found")
        raise HTTPException(status_code=404, detail="Session not found")

    if get_provider_mode() == "agent":
        reachable, reason = check_agent_health()
        if not reachable:
            raise HTTPException(
                status_code=503,
                detail=(
                    f"Host sensor agent is not reachable at {get_agent_base_url()}. "
                    f"Reason: {reason}. Start the host agent and retry."
                ),
            )

    try:
        scheduled_epoch_s, wait_seconds = session_manager.schedule_start(session_id)

        persistence_init_success = session_manager.init_persistence(session_id)
        if not persistence_init_success:
            raise RuntimeError("Failed to initialize persistence backends")
        logger.info(
            f"Persistence initialized for session {session_id} "
            f"(mode={session_manager.persistence_mode})"
        )

        session_manager.start_session(session_id)
        logger.info(f"Session {session_id} marked as running with {len(session.active_connections)} connection(s)")

        task = asyncio.create_task(_run_session_acquisition(session_id))
        session_tasks[session_id] = task
        logger.debug(f"Created acquisition task for session {session_id}")

        return SessionStartResponse(
            session_id=session_id,
            scheduled_start_epoch_s=scheduled_epoch_s,
            wait_seconds=wait_seconds,
            message=f"Session scheduled to start in {wait_seconds:.1f}s at {scheduled_epoch_s}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting session {session_id}: {type(e).__name__}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/sessions/{session_id}/stop")
async def stop_session(session_id: str):
    """Stop data collection."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        session_manager.stop_session(session_id)

        task = session_tasks.pop(session_id, None)
        if task and not task.done():
            task.cancel()

        session_manager.close_persistence(session_id)
        csv_files = session_manager.get_csv_files(session_id)
        files_info = [f.name for f in csv_files]
        persisted_rows = _count_csv_data_rows(csv_files)

        logger.info(f"Session {session_id} stopped. Generated {len(files_info)} CSV file(s): {files_info}")
        return {
            "session_id": session_id,
            "message": "Session stopped",
            "csv_files_generated": files_info,
            "total_samples_streamed": session.sample_count,
            "total_samples_persisted": persisted_rows,
            "total_samples": persisted_rows,
            "session_directory": str((session.export_root or session_manager.data_dir) / session_id),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/sessions/{session_id}/csv")
async def download_session_csv(session_id: str):
    """Download session data as one merged CSV string.

    If part files exist on disk, merge them in order. Otherwise fallback to
    in-memory samples for backwards compatibility.
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        csv_files = session_manager.get_csv_files(session_id)
        if csv_files:
            csv_content = _merge_session_csv(csv_files)
            filename = _build_export_filename(
                session_id,
                "csv",
                reference_dt=_session_reference_datetime(session),
            )
            return {
                "session_id": session_id,
                "csv_data": csv_content,
                "filename": filename,
            }

        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=session.csv_header)
        writer.writeheader()

        for sample in session.samples:
            row = {"timestamp": sample["timestamp_iso"]}
            for conn in session.active_connections:
                row[conn.name] = sample["values"].get(conn.name, "")
            writer.writerow(row)

        csv_content = output.getvalue()
        output.close()

        return {
            "session_id": session_id,
            "csv_data": csv_content,
            "filename": _build_export_filename(
                session_id,
                "csv",
                reference_dt=_session_reference_datetime(session),
            ),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/history")
async def get_history(page: int = 1, page_size: int = 10):
    """Return paginated collection history from persisted session folders."""
    try:
        page = max(1, page)
        page_size = max(1, min(100, page_size))

        items = []
        for session_folder in session_manager.data_dir.iterdir():
            if not session_folder.is_dir():
                continue

            session_id = session_folder.name
            if not SESSION_ID_PATTERN.fullmatch(session_id):
                continue

            csv_files = sorted(session_folder.glob("session_*.csv"))
            if not csv_files:
                continue

            total_size = sum(f.stat().st_size for f in csv_files)
            last_updated_epoch = max(f.stat().st_mtime for f in csv_files)
            last_updated = from_epoch_in_host_timezone(last_updated_epoch).isoformat()

            items.append(
                {
                    "session_id": session_id,
                    "file_count": len(csv_files),
                    "total_size_bytes": total_size,
                    "last_updated": last_updated,
                }
            )

        items.sort(key=lambda x: x["last_updated"], reverse=True)
        total_items = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        paged = items[start:end]

        return {
            "items": paged,
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": (total_items + page_size - 1) // page_size,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/history/{session_id}/download")
async def download_history_session(session_id: str):
    """Download a persisted historical collection as one merged CSV."""
    _validate_session_id(session_id)

    try:
        csv_files = _list_session_csv_files(session_id)
        if not csv_files:
            raise HTTPException(status_code=404, detail="Session not found")

        csv_content = _merge_session_csv(csv_files)
        reference_dt = from_epoch_in_host_timezone(max(f.stat().st_mtime for f in csv_files))
        return {
            "session_id": session_id,
            "csv_data": csv_content,
            "filename": _build_export_filename(session_id, "csv", reference_dt=reference_dt),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/history/{session_id}/download-parts")
async def download_history_session_parts(session_id: str):
    """Download all persisted CSV part files for a session as a ZIP archive."""
    _validate_session_id(session_id)

    try:
        csv_files = _list_session_csv_files(session_id)
        if not csv_files:
            raise HTTPException(status_code=404, detail="Session not found")

        archive = BytesIO()
        with zipfile.ZipFile(archive, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for csv_file in csv_files:
                zf.write(csv_file, arcname=csv_file.name)

        reference_dt = from_epoch_in_host_timezone(max(f.stat().st_mtime for f in csv_files))
        archive_filename = _build_export_filename(
            session_id,
            "zip",
            reference_dt=reference_dt,
            suffix="parts",
        )

        return Response(
            content=archive.getvalue(),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{archive_filename}"'
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/history/{session_id}")
async def delete_history_session(session_id: str):
    """Permanently delete all CSV files and folder for a persisted session."""
    _validate_session_id(session_id)

    session_folder = session_manager.data_dir / session_id
    if not session_folder.exists() or not session_folder.is_dir():
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        import shutil
        shutil.rmtree(session_folder)
        logger.info(f"Deleted session folder: {session_folder}")
        return {"session_id": session_id, "deleted": True}
    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/sessions/{session_id}")
async def websocket_session(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for live session updates."""
    logger.debug(f"WebSocket connection attempt for session {session_id}")
    
    session = session_manager.get_session(session_id)
    if not session:
        logger.warning(f"WebSocket connection rejected: session {session_id} not found")
        await websocket.close(code=1008, reason="Session not found")
        return

    await websocket.accept()
    active_websockets[session_id] = websocket
    logger.info(f"WebSocket connected for session {session_id}")

    try:
        # Keep connection open for sample streaming
        # Don't block on receive; instead, use a timeout and loop
        while session_id in active_websockets:
            try:
                # Wait for client messages with timeout (don't block indefinitely)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                logger.debug(f"WebSocket received message: {data}")
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                # Timeout is ok; just keep the connection alive
                logger.debug(f"WebSocket timeout for session {session_id}, continuing...")
                continue
            except Exception as e:
                # Client disconnected or error occurred
                logger.warning(f"WebSocket exception for session {session_id}: {type(e).__name__}: {e}")
                break
    except WebSocketDisconnect:
        logger.debug(f"WebSocket disconnected for session {session_id}")
    finally:
        if session_id in active_websockets:
            del active_websockets[session_id]
            logger.info(f"WebSocket cleaned up for session {session_id}")


async def _run_session_acquisition(session_id: str):
    """Background task to run real sensor acquisition for the session."""
    logger.debug(f"Acquisition task started for session {session_id}")
    
    session = session_manager.get_session(session_id)
    if not session:
        logger.error(f"Acquisition task: session {session_id} not found")
        return

    # Initialize sensor clients for each connection
    sensor_clients: dict = {}  # connection_name -> client
    connection_status: dict = {}  # connection_name -> status string
    stream_buffers: dict[str, str] = {}
    latest_distance_0p1mm: dict[str, int] = {}
    
    try:
        sample_interval = 1.0 / session.config.frequency_hz
        interval_ms = max(1, int(round(sample_interval * 1000.0)))
        measuring_mode = session.config.measuring_mode.value
        measuring_mode_code = MEASURING_MODE_CODE.get(measuring_mode, 0)
        effective_max_hz = get_effective_max_hz(session.config.baud_rate, measuring_mode)

        if session.config.frequency_hz > effective_max_hz:
            logger.error(
                f"Requested frequency {session.config.frequency_hz} Hz exceeds effective max "
                f"{effective_max_hz} Hz for baud {session.config.baud_rate} and mode {measuring_mode}"
            )
            return

        # Connect to all sensors
        for conn in session.active_connections:
            logger.info(f"Initializing sensor for {conn.name} on {conn.port}")
            client = create_sensor_client(
                port=conn.port,
                sensor_id=0,
                debug=False,
                baudrate=session.config.baud_rate,
                serial_profile=session.config.serial_profile.value,
                timeout=max(0.25, min(1.0, sample_interval * 2.0)),
            )
            
            if client.connect():
                logger.info(f"Connected to sensor {conn.name} on {conn.port}")

                if hasattr(client, "set_measuring_mode"):
                    ok_mode = client.set_measuring_mode(measuring_mode_code)
                    if not ok_mode:
                        logger.warning(
                            f"Failed to set measuring mode {measuring_mode} ({measuring_mode_code}) for {conn.name}"
                        )

                tracking_response = None
                if measuring_mode == "timed" and hasattr(client, "start_timed_tracking"):
                    tracking_response = client.start_timed_tracking(interval_ms)
                elif hasattr(client, "start_continuous_tracking"):
                    tracking_response = client.start_continuous_tracking()

                if not tracking_response and hasattr(client, "start_timed_tracking"):
                    tracking_response = client.start_timed_tracking(interval_ms)

                if tracking_response:
                    connection_status[conn.name] = "Collecting"
                    logger.info(
                        f"Tracking started for {conn.name} at {session.config.frequency_hz}Hz "
                        f"(interval={interval_ms}ms, baud={session.config.baud_rate}, mode={measuring_mode})"
                    )
                else:
                    logger.warning(f"Tracking start had no response from {conn.name}")
                    connection_status[conn.name] = "Ready"

                sensor_clients[conn.name] = client
                stream_buffers[conn.name] = ""
            else:
                logger.error(f"Failed to connect to sensor {conn.name} on {conn.port}")
                connection_status[conn.name] = "Error"
        
        # Update session with connection statuses
        session.connections_status = connection_status
        
        if not sensor_clients:
            logger.error(f"No sensors connected for session {session_id}")
            return
        
        # Wait for scheduled start
        if session.scheduled_start_epoch_s:
            wait = max(0, session.scheduled_start_epoch_s - time.time())
            logger.debug(f"Acquisition task waiting {wait:.2f}s until scheduled start for session {session_id}")
            await asyncio.sleep(wait)

        logger.info(f"Acquisition task starting real sensor collection for session {session_id}, frequency={session.config.frequency_hz}Hz, interval={sample_interval:.3f}s")

        async def emit_sample(values: dict[str, str]) -> None:
            """Record one already-assembled sample and emit to websocket."""
            if not values:
                logger.warning(f"No successful measurements for session {session_id}")
                return

            now = time.time()
            timestamp = from_epoch_in_host_timezone(now).isoformat()
            session_manager.record_sample(
                session_id,
                timestamp,
                int(now * 1000),
                values,
            )

            session_manager.write_sample_to_persistence(session_id, timestamp, int(now * 1000), values)

            if session_id in active_websockets:
                try:
                    await active_websockets[session_id].send_json(
                        {
                            "type": "sample",
                            "timestamp": timestamp,
                            "values": values,
                            "sample_count": session.sample_count,
                        }
                    )
                except Exception as e:
                    if session_id in active_websockets:
                        del active_websockets[session_id]
                    logger.error(f"WebSocket send failed for session {session_id}: {type(e).__name__}: {e}")

        try:
            sample_count = 0
            next_emit_at = time.perf_counter() + sample_interval
            while session.is_running:
                for conn in session.active_connections:
                    client = sensor_clients.get(conn.name)
                    if not client or not client.is_connected():
                        continue

                    try:
                        chunk = client.read_stream_chunk() if hasattr(client, "read_stream_chunk") else None
                        if not chunk:
                            continue

                        stream_buffers[conn.name] = stream_buffers.get(conn.name, "") + chunk
                        parts = stream_buffers[conn.name].split("\n")
                        stream_buffers[conn.name] = parts.pop() if parts else ""

                        for raw_line in parts:
                            line = raw_line.strip()
                            if not line:
                                continue
                            distance_0p1mm = parse_distance_response(line)
                            if distance_0p1mm is not None:
                                latest_distance_0p1mm[conn.name] = distance_0p1mm
                    except Exception as e:
                        logger.error(f"Error reading stream from sensor {conn.name}: {type(e).__name__}: {e}")
                        connection_status[conn.name] = "Error"

                now_perf = time.perf_counter()
                if now_perf >= next_emit_at:
                    values: dict[str, str] = {}
                    for conn in session.active_connections:
                        distance_0p1mm = latest_distance_0p1mm.get(conn.name)
                        if distance_0p1mm is None:
                            continue
                        distance_unit = convert_0p1mm_to_unit(distance_0p1mm, session.config.unit)
                        values[conn.name] = f"{distance_unit:.{session.config.decimal_places}f} {session.config.unit.value}"

                    sample_count += 1
                    logger.debug(f"Acquisition task emitting sample #{sample_count} for session {session_id}")
                    await emit_sample(values)

                    while next_emit_at <= now_perf:
                        next_emit_at += sample_interval

                sleep_for = max(0.001, min(0.01, next_emit_at - time.perf_counter()))
                await asyncio.sleep(sleep_for)
        except asyncio.CancelledError:
            logger.info(f"Acquisition task cancelled for session {session_id}")
        except Exception as e:
            logger.error(f"Acquisition task error for session {session_id}: {type(e).__name__}: {e}")
        
    finally:
        # Turn off lasers and disconnect all sensors
        logger.info(f"Shutting down sensors for session {session_id}")
        for conn_name, client in sensor_clients.items():
            try:
                logger.debug(f"Stopping tracking for {conn_name}")
                if hasattr(client, "stop_measurement"):
                    client.stop_measurement()
                else:
                    client.laser_off()
                client.disconnect()
            except Exception as e:
                logger.error(f"Error shutting down sensor {conn_name}: {type(e).__name__}: {e}")
        session_manager.close_persistence(session_id)
        session_tasks.pop(session_id, None)
        logger.debug(f"Acquisition task finished for session {session_id}")


@app.get("/api/sessions/{session_id}/csv-files")
async def list_csv_files(session_id: str):
    """List all CSV files generated for the session."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        csv_files = session_manager.get_csv_files(session_id)
        files_info = []
        for csv_file in csv_files:
            size = csv_file.stat().st_size
            files_info.append({
                "filename": csv_file.name,
                "size_bytes": size,
                "path": str(csv_file)
            })
        
        return {
            "session_id": session_id,
            "total_files": len(files_info),
            "files": files_info,
            "sample_count": session.sample_count,
            "session_directory": str((session.export_root or session_manager.data_dir) / session_id),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/sessions/{session_id}/csv-download/{filename}")
async def download_csv_file(session_id: str, filename: str):
    """Download a specific CSV file for the session."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # Validate filename format to prevent directory traversal
        if (
            not filename.startswith(f"session_{session_id}_")
            or not filename.endswith(".csv")
            or "/" in filename
            or "\\" in filename
            or ".." in filename
        ):
            raise HTTPException(status_code=403, detail="Invalid filename")
        
        session_dir = (session.export_root or session_manager.data_dir) / session_id
        file_path = session_dir / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            csv_content = f.read()
        
        return {
            "session_id": session_id,
            "filename": filename,
            "csv_data": csv_content
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
