"""Core session and acquisition management."""

import time
import uuid
import csv
import os
import sqlite3
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass, field

from app.models.schemas import SessionConnection, SessionConfig
from app.services.timezone import format_host_datetime_for_filename, now_in_host_timezone


def next_five_second_boundary(epoch_seconds: float) -> float:
    """Return the next immediate whole second divisible by 5."""
    import math
    whole_second = math.ceil(epoch_seconds)
    remainder = whole_second % 5
    if remainder == 0:
        return float(whole_second)
    return float(whole_second + (5 - remainder))


@dataclass
class AcquisitionSession:
    """In-memory session state."""
    session_id: str
    config: SessionConfig
    active_connections: List[SessionConnection]
    is_running: bool = False
    sample_count: int = 0
    start_time: Optional[str] = None
    scheduled_start_epoch_s: Optional[float] = None
    connections_status: Dict[str, str] = field(default_factory=dict)
    samples: List[dict] = field(default_factory=list)
    csv_file: Optional[Path] = None
    csv_file_handle: Optional[object] = None
    csv_writer: Optional[object] = None
    csv_header: Optional[List[str]] = None
    csv_row_count: int = 0
    csv_file_index: int = 1
    csv_filename_timestamp_label: Optional[str] = None
    csv_files_generated: List[str] = field(default_factory=list)
    export_root: Optional[Path] = None
    sqlite_db: Optional[Path] = None
    sqlite_conn: Optional[sqlite3.Connection] = None
    sqlite_sample_index: int = 0
    sqlite_since_commit: int = 0


class SessionManager:
    """Manages active acquisition sessions."""

    def __init__(self, data_dir: Path = None):
        """Initialize session manager."""
        self.sessions: Dict[str, AcquisitionSession] = {}
        self.data_dir = data_dir or (Path.cwd() / "data_dir")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.durable_writes = str(os.getenv("AS1100_DURABLE_WRITES", "1")).strip().lower() in {"1", "true", "yes", "on"}
        self.fsync_interval_rows = max(1, int(os.getenv("AS1100_FSYNC_INTERVAL_ROWS", "1")))
        raw_mode = str(os.getenv("AS1100_PERSISTENCE_MODE", "dual")).strip().lower()
        self.persistence_mode = raw_mode if raw_mode in {"csv", "sqlite", "dual"} else "dual"
        self.sqlite_commit_interval_rows = max(1, int(os.getenv("AS1100_SQLITE_COMMIT_INTERVAL_ROWS", "1")))

    def should_write_csv(self, session: Optional[AcquisitionSession] = None) -> bool:
        csv_enabled = self.persistence_mode in {"csv", "dual"}
        if session is None:
            return csv_enabled
        return csv_enabled and bool(session.config.export_csv)

    def should_write_sqlite(self) -> bool:
        return self.persistence_mode in {"sqlite", "dual"}

    @staticmethod
    def _sync_directory(path: Path) -> None:
        """Best-effort directory fsync to persist metadata updates."""
        try:
            fd = os.open(str(path), os.O_RDONLY)
        except Exception:
            return
        try:
            os.fsync(fd)
        except Exception:
            pass
        finally:
            try:
                os.close(fd)
            except Exception:
                pass

    def _sync_file(self, session: AcquisitionSession) -> None:
        """Best-effort durable sync for active CSV file."""
        if not session.csv_file_handle:
            return
        try:
            session.csv_file_handle.flush()
            if self.durable_writes:
                os.fsync(session.csv_file_handle.fileno())
                if session.csv_file:
                    self._sync_directory(session.csv_file.parent)
        except Exception:
            # Durability sync should never crash acquisition loop.
            pass

    def create_session(self, config: SessionConfig) -> AcquisitionSession:
        """Create a new session."""
        session_id = str(uuid.uuid4())[:8]
        active_conns = [c for c in config.connections if c.active]
        
        session = AcquisitionSession(
            session_id=session_id,
            config=config,
            active_connections=active_conns,
        )
        
        # Initialize connection status
        for conn in active_conns:
            session.connections_status[conn.name] = "Ready"
        
        # Initialize CSV header for multi-connection export
        session.csv_header = ["timestamp"] + [c.name for c in active_conns]
        
        self.sessions[session_id] = session
        return session

    def init_persistence(self, session_id: str) -> bool:
        """Initialize configured persistence backends for a session."""
        session = self.get_session(session_id)
        if not session:
            return False

        if self.should_write_csv(session):
            if not self.init_csv_export(session_id):
                return False

        if self.should_write_sqlite():
            if not self.init_sqlite_export(session_id):
                return False

        return True

    def write_sample_to_persistence(
        self,
        session_id: str,
        timestamp_iso: str,
        epoch_ms: int,
        values: Dict[str, str],
    ) -> bool:
        """Write sample to all configured persistence backends."""
        session = self.get_session(session_id)
        if not session:
            return False

        ok = True
        if self.should_write_csv(session):
            ok = self.write_sample_to_csv(session_id, timestamp_iso, values) and ok
        if self.should_write_sqlite():
            ok = self.write_sample_to_sqlite(session_id, timestamp_iso, epoch_ms, values) and ok
        return ok

    def close_persistence(self, session_id: str) -> None:
        """Close configured persistence backends."""
        self.close_csv_export(session_id)
        self.close_sqlite_export(session_id)

    def get_session(self, session_id: str) -> Optional[AcquisitionSession]:
        """Retrieve session by ID."""
        return self.sessions.get(session_id)

    def schedule_start(self, session_id: str) -> tuple[float, float]:
        """Schedule session to start at next 5-second boundary.
        
        Returns:
            (scheduled_epoch_s, wait_seconds)
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        now = time.time()
        scheduled = next_five_second_boundary(now)
        wait = max(0.0, scheduled - now)
        
        session.scheduled_start_epoch_s = scheduled
        return scheduled, wait

    def start_session(self, session_id: str) -> None:
        """Mark session as running."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        session.is_running = True
        session.start_time = now_in_host_timezone().isoformat()
        session.sample_count = 0

    def stop_session(self, session_id: str) -> None:
        """Stop session and finalize."""
        session = self.get_session(session_id)
        if not session:
            return
        
        session.is_running = False

    def record_sample(
        self,
        session_id: str,
        timestamp_iso: str,
        epoch_ms: int,
        values: Dict[str, str],  # connection_name -> "value unit"
    ) -> None:
        """Record a sample (potentially with multiple connection readings)."""
        session = self.get_session(session_id)
        if not session:
            return
        
        session.sample_count += 1
        
        # Store sample for WebSocket broadcast and CSV
        sample = {
            "timestamp_iso": timestamp_iso,
            "epoch_ms": epoch_ms,
            "values": values,  # per-connection readings
        }
        session.samples.append(sample)

    @staticmethod
    def _build_csv_part_filename(session: AcquisitionSession, part_index: int) -> str:
        """Build a host-local timestamped CSV part filename."""
        timestamp_label = session.csv_filename_timestamp_label or format_host_datetime_for_filename()
        return f"session_{session.session_id}_{timestamp_label}_part_{part_index}.csv"

    def init_csv_export(self, session_id: str) -> bool:
        """Initialize CSV export file for the session."""
        session = self.get_session(session_id)
        if not session or not session.config.export_csv:
            return False

        try:
            session.export_root = self.data_dir

            # Create session data directory
            session_dir = session.export_root / session_id
            session_dir.mkdir(parents=True, exist_ok=True)

            # Generate first CSV filename
            session.csv_filename_timestamp_label = format_host_datetime_for_filename()
            csv_filename = self._build_csv_part_filename(session, 1)
            csv_path = session_dir / csv_filename

            # Open file and create CSV writer
            session.csv_file = csv_path
            session.csv_file_handle = open(csv_path, 'w', newline='', encoding='utf-8')
            session.csv_writer = csv.DictWriter(session.csv_file_handle, fieldnames=session.csv_header)
            session.csv_writer.writeheader()
            self._sync_file(session)
            session.csv_row_count = 0
            session.csv_file_index = 1
            session.csv_files_generated.append(csv_filename)

            return True
        except Exception as e:
            print(f"Error initializing CSV export for session {session_id}: {e}")
            return False

    def init_sqlite_export(self, session_id: str) -> bool:
        """Initialize SQLite durability store for the session."""
        session = self.get_session(session_id)
        if not session:
            return False

        try:
            session.export_root = self.data_dir
            session_dir = session.export_root / session_id
            session_dir.mkdir(parents=True, exist_ok=True)

            db_path = session_dir / f"session_{session_id}.db"
            conn = sqlite3.connect(str(db_path), timeout=30.0)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=FULL;" if self.durable_writes else "PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA busy_timeout=5000;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sample_index INTEGER NOT NULL,
                    timestamp_iso TEXT NOT NULL,
                    epoch_ms INTEGER NOT NULL,
                    connection_name TEXT NOT NULL,
                    value TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_samples_session ON samples(sample_index, connection_name);"
            )
            conn.commit()

            session.sqlite_db = db_path
            session.sqlite_conn = conn
            session.sqlite_sample_index = 0
            session.sqlite_since_commit = 0
            return True
        except Exception as e:
            print(f"Error initializing SQLite export for session {session_id}: {e}")
            try:
                if session.sqlite_conn:
                    session.sqlite_conn.close()
            except Exception:
                pass
            session.sqlite_conn = None
            session.sqlite_db = None
            return False

    def write_sample_to_csv(self, session_id: str, timestamp_iso: str, values: Dict[str, str]) -> bool:
        """Write a sample to the CSV file (with automatic rotation)."""
        session = self.get_session(session_id)
        if not session or not session.csv_writer:
            return False
        
        try:
            rows_per_file = max(1, int(session.config.rows_per_file))
            # Check if we need to rotate file
            if session.csv_row_count >= rows_per_file:
                self._rotate_csv_file(session_id)
            
            # Write the row
            row = {"timestamp": timestamp_iso}
            for conn in session.active_connections:
                row[conn.name] = values.get(conn.name, "")
            session.csv_writer.writerow(row)
            session.csv_row_count += 1

            if (session.csv_row_count % self.fsync_interval_rows) == 0:
                self._sync_file(session)
            
            return True
        except Exception as e:
            print(f"Error writing to CSV for session {session_id}: {e}")
            return False

    def write_sample_to_sqlite(
        self,
        session_id: str,
        timestamp_iso: str,
        epoch_ms: int,
        values: Dict[str, str],
    ) -> bool:
        """Write a sample to SQLite for durable ingestion ledger."""
        session = self.get_session(session_id)
        if not session or not session.sqlite_conn:
            return False

        try:
            session.sqlite_sample_index += 1
            rows = [
                (
                    session.sqlite_sample_index,
                    timestamp_iso,
                    epoch_ms,
                    conn.name,
                    values.get(conn.name, ""),
                )
                for conn in session.active_connections
            ]

            session.sqlite_conn.executemany(
                """
                INSERT INTO samples(sample_index, timestamp_iso, epoch_ms, connection_name, value)
                VALUES (?, ?, ?, ?, ?)
                """,
                rows,
            )
            session.sqlite_since_commit += 1

            if session.sqlite_since_commit >= self.sqlite_commit_interval_rows:
                session.sqlite_conn.commit()
                session.sqlite_since_commit = 0
            return True
        except Exception as e:
            print(f"Error writing to SQLite for session {session_id}: {e}")
            try:
                session.sqlite_conn.rollback()
            except Exception:
                pass
            return False

    def _rotate_csv_file(self, session_id: str) -> bool:
        """Create a new CSV file when row limit is reached."""
        session = self.get_session(session_id)
        if not session:
            return False
        
        try:
            # Close current file
            if session.csv_file_handle:
                self._sync_file(session)
                session.csv_file_handle.close()
            
            # Create new file
            session.csv_file_index += 1
            csv_filename = self._build_csv_part_filename(session, session.csv_file_index)
            export_root = session.export_root or self.data_dir
            session_dir = export_root / session_id
            csv_path = session_dir / csv_filename
            
            # Open new file with header
            session.csv_file = csv_path
            session.csv_file_handle = open(csv_path, 'w', newline='', encoding='utf-8')
            session.csv_writer = csv.DictWriter(session.csv_file_handle, fieldnames=session.csv_header)
            session.csv_writer.writeheader()
            self._sync_file(session)
            session.csv_row_count = 0
            session.csv_files_generated.append(csv_filename)
            
            return True
        except Exception as e:
            print(f"Error rotating CSV file for session {session_id}: {e}")
            return False

    def close_csv_export(self, session_id: str) -> None:
        """Close CSV file handle."""
        session = self.get_session(session_id)
        if not session or not session.csv_file_handle:
            return
        
        try:
            self._sync_file(session)
            session.csv_file_handle.close()
            session.csv_file_handle = None
            session.csv_writer = None
        except Exception as e:
            print(f"Error closing CSV export for session {session_id}: {e}")

    def close_sqlite_export(self, session_id: str) -> None:
        """Close SQLite connection for the session."""
        session = self.get_session(session_id)
        if not session or not session.sqlite_conn:
            return

        try:
            session.sqlite_conn.commit()
            session.sqlite_conn.close()
            session.sqlite_conn = None
            session.sqlite_since_commit = 0
        except Exception as e:
            print(f"Error closing SQLite export for session {session_id}: {e}")

    def get_csv_files(self, session_id: str) -> List[Path]:
        """Get list of CSV files generated for the session."""
        session = self.get_session(session_id)
        if not session:
            return []
        
        export_root = session.export_root or self.data_dir
        session_dir = export_root / session_id
        if not session_dir.exists():
            return []
        
        return sorted(session_dir.glob("session_*.csv"))

    def delete_session(self, session_id: str) -> None:
        """Remove session from memory."""
        if session_id in self.sessions:
            del self.sessions[session_id]

    def get_all_sessions(self) -> List[AcquisitionSession]:
        """Get all active sessions."""
        return list(self.sessions.values())

