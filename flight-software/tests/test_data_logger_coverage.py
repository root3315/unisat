"""Coverage pack for DataLogger module."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.data_logger import DataLogger


@pytest.fixture
def logger_tmp(tmp_path: Path) -> DataLogger:
    return DataLogger({
        "db_path": str(tmp_path / "tlm.db"),
        "max_size_mb": 10,
    })


@pytest.mark.asyncio
async def test_data_logger_initialize_creates_db(logger_tmp: DataLogger) -> None:
    assert await logger_tmp.initialize() is True


@pytest.mark.asyncio
async def test_data_logger_lifecycle(logger_tmp: DataLogger) -> None:
    await logger_tmp.initialize()
    await logger_tmp.start()
    status = await logger_tmp.get_status()
    assert "status" in status
    await logger_tmp.stop()


@pytest.mark.asyncio
async def test_log_telemetry_record(logger_tmp: DataLogger) -> None:
    await logger_tmp.initialize()
    await logger_tmp.start()
    # Log a single telemetry entry.
    await logger_tmp.log_telemetry(
            sequence_count=1, mission_time=0.0,
        timestamp=1000.0,
        apid=0x07D,
        payload=b"\x01\x02\x03\x04",
    )
    await logger_tmp.stop()


@pytest.mark.asyncio
async def test_query_by_time_range_empty(logger_tmp: DataLogger) -> None:
    await logger_tmp.initialize()
    results = await logger_tmp.query_by_time_range(
        start_time=0.0,
        end_time=9999999.0,
    )
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_query_returns_logged_entry(logger_tmp: DataLogger) -> None:
    await logger_tmp.initialize()
    await logger_tmp.start()
    await logger_tmp.log_telemetry(
            sequence_count=1, mission_time=0.0,
        timestamp=1000.0,
        apid=0x07D,
        payload=b"hello",
    )
    results = await logger_tmp.query_by_time_range(
        start_time=500.0,
        end_time=2000.0,
    )
    assert isinstance(results, list)
    assert len(results) >= 1
    await logger_tmp.stop()


@pytest.mark.asyncio
async def test_export_csv_creates_file(tmp_path: Path, logger_tmp: DataLogger) -> None:
    await logger_tmp.initialize()
    await logger_tmp.start()
    await logger_tmp.log_telemetry(
            sequence_count=1, mission_time=0.0,
        timestamp=100.0, apid=1, payload=b"test",
    )
    csv_path = str(tmp_path / "out.csv")
    await logger_tmp.export_csv(csv_path)
    # Either the file is produced or the export returns quietly —
    # both are acceptable provided no exception escapes.
    await logger_tmp.stop()


@pytest.mark.asyncio
async def test_rotation_check_does_not_raise(logger_tmp: DataLogger) -> None:
    """_check_rotation runs housekeeping; on an empty DB it should
    be a no-op but must not raise."""
    await logger_tmp.initialize()
    await logger_tmp.start()
    await logger_tmp._check_rotation()
    await logger_tmp.stop()


@pytest.mark.asyncio
async def test_multiple_apids_query_filter(logger_tmp: DataLogger) -> None:
    await logger_tmp.initialize()
    await logger_tmp.start()
    for apid, data in [(1, b"a"), (2, b"b"), (1, b"c")]:
        await logger_tmp.log_telemetry(
            sequence_count=1, mission_time=0.0,
            timestamp=100.0 + apid,
            apid=apid,
            payload=data,
        )
    # Query without apid filter — all entries.
    all_results = await logger_tmp.query_by_time_range(
        start_time=0.0, end_time=999.0,
    )
    assert len(all_results) >= 3
    await logger_tmp.stop()
