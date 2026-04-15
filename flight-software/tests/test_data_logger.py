"""Tests for the DataLogger module."""

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.data_logger import DataLogger


@pytest.fixture
def logger_config(tmp_path):
    """Create a DataLogger config pointing to a temporary directory."""
    return {"db_dir": str(tmp_path / "data"), "max_db_size_gb": 0.001}


@pytest.fixture
async def data_logger(logger_config):
    """Initialize and yield a DataLogger, then stop it."""
    dl = DataLogger(logger_config)
    await dl.initialize()
    yield dl
    await dl.stop()


@pytest.mark.asyncio
async def test_database_creation(logger_config):
    dl = DataLogger(logger_config)
    result = await dl.initialize()
    assert result is True
    assert dl.current_db_path.exists()
    await dl.stop()


@pytest.mark.asyncio
async def test_store_telemetry(data_logger):
    ok = await data_logger.log_telemetry(
        timestamp=1000.0, apid=1, sequence_count=0,
        mission_time=100.0, payload=b"\x01\x02\x03",
    )
    assert ok is True
    assert data_logger._record_count == 1


@pytest.mark.asyncio
async def test_store_multiple_records(data_logger):
    for i in range(5):
        await data_logger.log_telemetry(
            timestamp=1000.0 + i, apid=1, sequence_count=i,
            mission_time=100.0 + i, payload=b"\xAA",
        )
    assert data_logger._record_count == 5


@pytest.mark.asyncio
async def test_query_by_time_range(data_logger):
    for i in range(10):
        await data_logger.log_telemetry(
            timestamp=1000.0 + i, apid=1, sequence_count=i,
            mission_time=float(i), payload=b"\xFF",
        )
    results = await data_logger.query_by_time_range(1003.0, 1007.0)
    assert len(results) == 5
    assert all(1003.0 <= r["timestamp"] <= 1007.0 for r in results)


@pytest.mark.asyncio
async def test_query_by_time_range_with_apid_filter(data_logger):
    await data_logger.log_telemetry(1000.0, apid=1, sequence_count=0, mission_time=0.0, payload=b"\x01")
    await data_logger.log_telemetry(1001.0, apid=2, sequence_count=1, mission_time=1.0, payload=b"\x02")
    await data_logger.log_telemetry(1002.0, apid=1, sequence_count=2, mission_time=2.0, payload=b"\x03")
    results = await data_logger.query_by_time_range(999.0, 1010.0, apid=1)
    assert len(results) == 2
    assert all(r["apid"] == 1 for r in results)


@pytest.mark.asyncio
async def test_csv_export(data_logger, tmp_path):
    for i in range(3):
        await data_logger.log_telemetry(
            timestamp=2000.0 + i, apid=5, sequence_count=i,
            mission_time=float(i), payload=b"\xDE\xAD",
        )
    csv_path = str(tmp_path / "export.csv")
    count = await data_logger.export_csv(csv_path)
    assert count == 3
    content = Path(csv_path).read_text()
    lines = content.strip().split("\n")
    assert lines[0] == "id,timestamp,apid,sequence_count,mission_time,payload_hex"
    assert len(lines) == 4  # header + 3 records


@pytest.mark.asyncio
async def test_query_empty_range_returns_empty(data_logger):
    await data_logger.log_telemetry(1000.0, 1, 0, 0.0, b"\x00")
    results = await data_logger.query_by_time_range(5000.0, 6000.0)
    assert results == []
