"""Live AX.25 TCP bridge for the Streamlit dashboard (roadmap item M2).

Runs a background thread that:

  1. Connects (or listens) on a TCP port.
  2. Feeds every received byte through :class:`utils.ax25.Ax25Decoder`.
  3. Records every successfully decoded frame in a bounded ring buffer.
  4. Optionally persists frames to SQLite so page reloads survive.

The bridge is thread-safe: callers may inspect :attr:`recent` at any
time and expect a consistent snapshot. There is no blocking inside the
critical section.

Design notes
------------
* We deliberately run as a client so the firmware-side SITL
  (``scripts/sitl_fw``) continues to act as the TCP server — mirrors
  the over-the-air direction where the radio is the "server".
* A lock-free ring would be overkill for < 10 Hz beacon cadence; a
  :class:`collections.deque` behind a :class:`threading.Lock` is
  sufficient and keeps the code understandable.
* ``push_raw()`` lets unit tests feed bytes directly without needing
  a socket pair; it is the only public write interface.
"""

from __future__ import annotations

import json
import socket
import sqlite3
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass
from typing import Optional

from utils.ax25 import AX25Error, Ax25Decoder


@dataclass(frozen=True)
class LiveFrame:
    """A decoded UI frame plus wall-clock metadata for the UI layer."""

    received_at: float  # unix timestamp
    dst_callsign: str
    dst_ssid: int
    src_callsign: str
    src_ssid: int
    pid: int
    info_hex: str
    fcs_valid: bool


class Ax25Bridge:
    """Background TCP → decoder → ring-buffer pipeline.

    Typical lifecycle::

        bridge = Ax25Bridge(host="127.0.0.1", port=52100, capacity=200)
        bridge.start()
        ...
        frames = bridge.recent(limit=20)
        ...
        bridge.stop()

    Callers may instead feed bytes directly via :py:meth:`push_raw` —
    this is the intended path for unit tests and for integrating a
    different transport (e.g. a real SDR demodulator pipe).
    """

    _STOP_SENTINEL = object()

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 52100,
        capacity: int = 200,
        sqlite_path: Optional[str] = None,
        reconnect_delay_s: float = 1.0,
        reconnect_max_delay_s: float = 30.0,
    ) -> None:
        self.host = host
        self.port = port
        self._capacity = capacity
        self._sqlite_path = sqlite_path
        # Exponential backoff on TCP failures: start at
        # reconnect_delay_s, double on every consecutive attempt,
        # cap at reconnect_max_delay_s. Prevents a fast reconnect
        # loop from saturating the local socket or a misconfigured
        # peer during a long outage.
        self._reconnect_delay_s = reconnect_delay_s
        self._reconnect_max_delay_s = reconnect_max_delay_s
        self._current_delay_s = reconnect_delay_s

        self._decoder = Ax25Decoder()
        self._buffer: deque[LiveFrame] = deque(maxlen=capacity)
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._sock: Optional[socket.socket] = None

        self._accepted = 0
        self._errors = 0
        self._bytes_in = 0
        self._connected = False
        self._last_error: Optional[str] = None

        self._sqlite = self._open_sqlite() if sqlite_path else None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Spawn the background worker. No-op if already running."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, name="ax25-bridge", daemon=True
        )
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        """Signal the worker to exit and close the socket."""
        self._stop_event.set()
        sock = self._sock
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None
        if self._sqlite is not None:
            self._sqlite.close()
            self._sqlite = None

    def push_raw(self, data: bytes) -> None:
        """Feed bytes into the decoder without going through the socket."""
        self._ingest(data)

    def recent(self, limit: Optional[int] = None) -> list[LiveFrame]:
        """Return a newest-first snapshot of the ring buffer."""
        with self._lock:
            snapshot = list(self._buffer)
        snapshot.reverse()
        if limit is not None:
            snapshot = snapshot[:limit]
        return snapshot

    def stats(self) -> dict[str, object]:
        """Return a monitoring snapshot for the Streamlit status bar."""
        with self._lock:
            buffered = len(self._buffer)
        return {
            "connected": self._connected,
            "accepted": self._accepted,
            "errors": self._errors,
            "bytes_in": self._bytes_in,
            "buffered": buffered,
            "capacity": self._capacity,
            "last_error": self._last_error,
        }

    # ------------------------------------------------------------------
    # Worker thread
    # ------------------------------------------------------------------
    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._connect_and_read()
                # A clean return means the peer closed the socket
                # gracefully — reset backoff so next reconnect is
                # fast.
                self._current_delay_s = self._reconnect_delay_s
            except Exception as exc:  # pragma: no cover — keep thread alive
                self._last_error = repr(exc)
                self._connected = False
            if self._stop_event.wait(self._current_delay_s):
                break
            # Double the delay up to the cap, so repeated failures
            # back off instead of hammering the local stack.
            self._current_delay_s = min(
                self._current_delay_s * 2.0, self._reconnect_max_delay_s
            )

    def _connect_and_read(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.0)
            sock.connect((self.host, self.port))
            self._sock = sock
            self._connected = True
            self._last_error = None
            while not self._stop_event.is_set():
                try:
                    data = sock.recv(1024)
                except socket.timeout:
                    continue
                except OSError:
                    break
                if not data:
                    break
                self._ingest(data)
        self._sock = None
        self._connected = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _ingest(self, data: bytes) -> None:
        self._bytes_in += len(data)
        for byte in data:
            try:
                frame = self._decoder.push_byte(byte)
            except AX25Error:
                self._errors += 1
                continue
            if frame is None:
                continue
            live = LiveFrame(
                received_at=time.time(),
                dst_callsign=frame.dst.callsign,
                dst_ssid=frame.dst.ssid,
                src_callsign=frame.src.callsign,
                src_ssid=frame.src.ssid,
                pid=frame.pid,
                info_hex=frame.info.hex(),
                fcs_valid=frame.fcs_valid,
            )
            with self._lock:
                self._buffer.append(live)
            self._accepted += 1
            if self._sqlite is not None:
                self._persist(live)

    def _open_sqlite(self) -> sqlite3.Connection:
        assert self._sqlite_path is not None
        conn = sqlite3.connect(
            self._sqlite_path, check_same_thread=False, isolation_level=None
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ax25_frames (
                received_at REAL NOT NULL,
                dst_callsign TEXT NOT NULL,
                dst_ssid INTEGER NOT NULL,
                src_callsign TEXT NOT NULL,
                src_ssid INTEGER NOT NULL,
                pid INTEGER NOT NULL,
                info_hex TEXT NOT NULL,
                fcs_valid INTEGER NOT NULL
            )
            """
        )
        return conn

    def _persist(self, frame: LiveFrame) -> None:
        assert self._sqlite is not None
        self._sqlite.execute(
            "INSERT INTO ax25_frames VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                frame.received_at,
                frame.dst_callsign,
                frame.dst_ssid,
                frame.src_callsign,
                frame.src_ssid,
                frame.pid,
                frame.info_hex,
                1 if frame.fcs_valid else 0,
            ),
        )


def frame_to_json(frame: LiveFrame) -> str:
    """Convenience helper for the UI / debug logs."""
    return json.dumps(asdict(frame), separators=(",", ":"))
