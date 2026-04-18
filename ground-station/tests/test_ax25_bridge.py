"""Unit tests for :mod:`utils.ax25_bridge` (roadmap item M2)."""

from __future__ import annotations

import socket
import sys
import threading
import time
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.ax25 import Address, encode_ui_frame
from utils.ax25_bridge import Ax25Bridge, LiveFrame, frame_to_json


# ---------------------------------------------------------------------------
# Pure-python tests: push_raw bypasses the network layer so they run in ms.
# ---------------------------------------------------------------------------


def _make_beacon(info: bytes = b"Hi") -> bytes:
    return encode_ui_frame(Address("CQ", 0), Address("UN8SAT", 1), 0xF0, info)


def test_push_raw_surfaces_a_single_frame() -> None:
    bridge = Ax25Bridge()
    bridge.push_raw(_make_beacon())

    recent = bridge.recent()
    assert len(recent) == 1
    frame = recent[0]
    assert frame.src_callsign == "UN8SAT"
    assert frame.src_ssid == 1
    assert frame.info_hex == b"Hi".hex()
    assert frame.fcs_valid is True

    stats = bridge.stats()
    assert stats["accepted"] == 1
    assert stats["errors"] == 0
    assert stats["buffered"] == 1


def test_ring_buffer_caps_at_capacity() -> None:
    bridge = Ax25Bridge(capacity=3)
    for idx in range(5):
        bridge.push_raw(_make_beacon(info=bytes([idx])))

    recent = bridge.recent()
    assert len(recent) == 3
    # Newest-first ordering — most recent idx (4) is first.
    assert recent[0].info_hex == bytes([4]).hex()
    assert recent[-1].info_hex == bytes([2]).hex()


def test_recent_limit_trims_from_newest() -> None:
    bridge = Ax25Bridge(capacity=10)
    for idx in range(4):
        bridge.push_raw(_make_beacon(info=bytes([idx])))

    top_two = bridge.recent(limit=2)
    assert [f.info_hex for f in top_two] == [bytes([3]).hex(), bytes([2]).hex()]


def test_garbage_bytes_count_as_errors_not_crashes() -> None:
    bridge = Ax25Bridge()
    bridge.push_raw(b"\xff\xff\xfe\xfd\xfc\xfb" * 50)  # 300 random-looking bytes
    stats = bridge.stats()
    assert stats["accepted"] == 0
    # Decoder should swallow garbage without raising.
    assert stats["bytes_in"] == 300


def test_stats_connected_flag_starts_false() -> None:
    bridge = Ax25Bridge()
    stats = bridge.stats()
    assert stats["connected"] is False
    assert stats["buffered"] == 0


def test_sqlite_persistence(tmp_path: Path) -> None:
    db = tmp_path / "frames.sqlite"
    bridge = Ax25Bridge(sqlite_path=str(db))
    try:
        bridge.push_raw(_make_beacon(info=b"abc"))
    finally:
        bridge.stop()

    import sqlite3

    rows = sqlite3.connect(db).execute(
        "SELECT src_callsign, info_hex, fcs_valid FROM ax25_frames"
    ).fetchall()
    assert rows == [("UN8SAT", b"abc".hex(), 1)]


def test_frame_to_json_roundtrip() -> None:
    frame = LiveFrame(
        received_at=1.5,
        dst_callsign="CQ",
        dst_ssid=0,
        src_callsign="UN8SAT",
        src_ssid=1,
        pid=0xF0,
        info_hex="deadbeef",
        fcs_valid=True,
    )
    payload = frame_to_json(frame)
    assert '"src_callsign":"UN8SAT"' in payload
    assert '"fcs_valid":true' in payload


# ---------------------------------------------------------------------------
# End-to-end over a real TCP socket pair. Skipped on systems where
# binding 127.0.0.1:* is not possible (rare).
# ---------------------------------------------------------------------------


def _run_server_once(
    host: str, port: int, payload: bytes, ready: threading.Event
) -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(1)
    ready.set()
    conn, _ = srv.accept()
    with conn:
        conn.sendall(payload)
    srv.close()


def test_tcp_end_to_end_feeds_the_decoder() -> None:
    host = "127.0.0.1"
    port = _free_tcp_port()

    ready = threading.Event()
    server = threading.Thread(
        target=_run_server_once,
        args=(host, port, _make_beacon(info=b"LIVE"), ready),
        daemon=True,
    )
    server.start()
    assert ready.wait(timeout=2.0), "test TCP server never became ready"

    bridge = Ax25Bridge(host=host, port=port, reconnect_delay_s=0.1)
    bridge.start()

    # Poll the ring buffer with a generous timeout; CI boxes can be slow.
    deadline = time.time() + 5.0
    while time.time() < deadline:
        if bridge.stats()["accepted"] >= 1:
            break
        time.sleep(0.05)

    bridge.stop()
    server.join(timeout=2.0)

    assert bridge.stats()["accepted"] == 1
    recent = bridge.recent()
    assert recent[0].info_hex == b"LIVE".hex()


def _free_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])
