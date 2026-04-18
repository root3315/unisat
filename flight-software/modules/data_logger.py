"""Data Logger for UniSat CubeSat.

Provides persistent telemetry storage using SQLite, CSV export, automatic
database rotation at configurable size thresholds, and time-range queries.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any

import aiofiles

from modules import BaseModule, ModuleStatus


class DataLogger(BaseModule):
    """Logs telemetry frames to SQLite with rotation and export.

    Attributes:
        db_dir: Directory where database files are stored.
        max_db_size: Maximum database size in bytes before rotation (default 1 GB).
        current_db_path: Path to the currently active database file.
    """

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS telemetry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp REAL NOT NULL,
        apid INTEGER NOT NULL,
        sequence_count INTEGER NOT NULL,
        mission_time REAL NOT NULL,
        payload BLOB NOT NULL,
        created_at REAL NOT NULL DEFAULT (strftime('%s', 'now'))
    );
    CREATE INDEX IF NOT EXISTS idx_telemetry_ts ON telemetry(timestamp);
    CREATE INDEX IF NOT EXISTS idx_telemetry_apid ON telemetry(apid);
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the data logger.

        Args:
            config: Configuration with optional 'db_dir' and 'max_db_size_gb'.
        """
        super().__init__("data_logger", config)
        self.db_dir = Path(self.config.get("db_dir", "./data"))
        max_gb = self.config.get("max_db_size_gb", 1.0)
        self.max_db_size: int = int(max_gb * 1024 * 1024 * 1024)
        self.current_db_path: Path = self.db_dir / "telemetry_current.db"
        self._conn: sqlite3.Connection | None = None
        self._record_count: int = 0

    async def initialize(self) -> bool:
        """Create database directory and initialize the SQLite schema.

        Returns:
            True if initialization succeeded.
        """
        try:
            self.db_dir.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.current_db_path), check_same_thread=False)
            self._conn.executescript(self.SCHEMA)
            self._conn.commit()
            cursor = self._conn.execute("SELECT COUNT(*) FROM telemetry")
            self._record_count = cursor.fetchone()[0]
            self.status = ModuleStatus.READY
            self.logger.info("Data logger ready, %d existing records", self._record_count)
            return True
        except (sqlite3.Error, OSError) as exc:
            self.record_error(f"DB init failed: {exc}")
            self.status = ModuleStatus.ERROR
            return False

    async def start(self) -> None:
        """Start the data logger."""
        self.status = ModuleStatus.RUNNING

    async def stop(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
        self.status = ModuleStatus.STOPPED
        self.logger.info("Data logger stopped, %d total records", self._record_count)

    async def get_status(self) -> dict[str, Any]:
        """Return data logger status.

        Returns:
            Dict with record count, database size, and path.
        """
        db_size = self.current_db_path.stat().st_size if self.current_db_path.exists() else 0
        return {
            "status": self.status.name,
            "record_count": self._record_count,
            "db_size_mb": round(db_size / (1024 * 1024), 2),
            "db_path": str(self.current_db_path),
            "error_count": self._error_count,
        }

    async def log_telemetry(self, timestamp: float, apid: int,
                            sequence_count: int, mission_time: float,
                            payload: bytes) -> bool:
        """Write a telemetry record to the database.

        Args:
            timestamp: Unix timestamp of the measurement.
            apid: CCSDS Application Process Identifier.
            sequence_count: Packet sequence counter.
            mission_time: Mission elapsed time in seconds.
            payload: Raw telemetry payload bytes.

        Returns:
            True if the record was stored.
        """
        if not self._conn:
            self.record_error("Database not connected")
            return False
        try:
            self._conn.execute(
                "INSERT INTO telemetry (timestamp, apid, sequence_count, mission_time, payload) "
                "VALUES (?, ?, ?, ?, ?)",
                (timestamp, apid, sequence_count, mission_time, payload),
            )
            self._conn.commit()
            self._record_count += 1
            await self._check_rotation()
            return True
        except sqlite3.Error as exc:
            self.record_error(f"Insert failed: {exc}")
            return False

    async def query_by_time_range(self, start_time: float, end_time: float,
                                  apid: int | None = None) -> list[dict[str, Any]]:
        """Query telemetry records within a time range.

        Args:
            start_time: Start Unix timestamp (inclusive).
            end_time: End Unix timestamp (inclusive).
            apid: Optional APID filter.

        Returns:
            List of record dictionaries.
        """
        if not self._conn:
            return []
        query = "SELECT id, timestamp, apid, sequence_count, mission_time, payload FROM telemetry WHERE timestamp >= ? AND timestamp <= ?"
        params: list[Any] = [start_time, end_time]
        if apid is not None:
            query += " AND apid = ?"
            params.append(apid)
        query += " ORDER BY timestamp ASC"
        cursor = self._conn.execute(query, params)
        columns = ["id", "timestamp", "apid", "sequence_count", "mission_time", "payload"]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    async def export_csv(self, output_path: str, start_time: float | None = None,
                         end_time: float | None = None) -> int:
        """Export telemetry records to a CSV file.

        Args:
            output_path: Filesystem path for the CSV output.
            start_time: Optional start timestamp filter.
            end_time: Optional end timestamp filter.

        Returns:
            Number of records exported.
        """
        start = start_time or 0.0
        end = end_time or time.time() + 86400
        records = await self.query_by_time_range(start, end)
        async with aiofiles.open(output_path, mode="w", newline="") as f:
            header = "id,timestamp,apid,sequence_count,mission_time,payload_hex\n"
            await f.write(header)
            for rec in records:
                payload_hex = rec["payload"].hex() if isinstance(rec["payload"], bytes) else str(rec["payload"])
                line = f"{rec['id']},{rec['timestamp']},{rec['apid']},{rec['sequence_count']},{rec['mission_time']},{payload_hex}\n"
                await f.write(line)
        self.logger.info("Exported %d records to %s", len(records), output_path)
        return len(records)

    async def _check_rotation(self) -> None:
        """Rotate the database file if it exceeds the size limit."""
        if not self.current_db_path.exists():
            return
        size = self.current_db_path.stat().st_size
        if size < self.max_db_size:
            return
        self.logger.warning("Database size %d MB exceeds limit, rotating", size // (1024 * 1024))
        if self._conn:
            self._conn.close()
        archive_name = f"telemetry_{int(time.time())}.db"
        archive_path = self.db_dir / archive_name
        self.current_db_path.rename(archive_path)
        self._conn = sqlite3.connect(str(self.current_db_path), check_same_thread=False)
        self._conn.executescript(self.SCHEMA)
        self._conn.commit()
        self._record_count = 0
        self.logger.info("Rotated database to %s", archive_name)
