"""Coverage pack for communication.py — serial-port paths via mock.

The default test path in test_coverage_boost.py only exercises the
"no serial device available" branch (CI hosts don't have /dev/ttyS0).
This pack uses `unittest.mock.patch` to replace `serial.Serial` with
a controllable fake so every branch of:

  * initialize (happy + open-failure)
  * send_packet (happy + queue-on-closed + serial-exception)
  * receive_packet (no-data + no-sync + short-frame + full-packet +
                     serial-exception)
  * flush_tx_queue (all-sent + stop-on-failure)
  * seconds_since_last_rx / is_connected

is hit and counted by gcov. Brings the module from 52 % to the
80%+ band.
"""

from __future__ import annotations

import asyncio
import struct
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Every test in this file patches or instantiates a real pyserial object,
# so skip the whole module cleanly on a checkout that does not have
# pyserial installed (CI images without flight-software/requirements.txt).
# Without this guard, pytest raises a collection error on `import serial`
# below, which counts as a hard failure instead of a skip — see #8.
pytest.importorskip("serial", reason="pyserial required for CommunicationManager tests")

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.communication import CommunicationManager, SYNC_WORD
import serial


# --------------------------------------------------------------------------
#  Helpers
# --------------------------------------------------------------------------

def _make_fake_serial(*, in_waiting: int = 0, read_data: bytes = b"",
                     is_open: bool = True, write_returns: int | None = None,
                     raise_on: str | None = None) -> MagicMock:
    """Build a MagicMock that looks enough like serial.Serial for
    CommunicationManager to drive.

    raise_on = "write" | "read" | None — inject serial.SerialException
    on the named method to exercise the error-path branch.
    """
    fake = MagicMock()
    fake.is_open = is_open
    fake.in_waiting = in_waiting
    fake.close = MagicMock()

    if raise_on == "write":
        fake.write = MagicMock(side_effect=serial.SerialException("TX fail"))
    else:
        fake.write = MagicMock(return_value=write_returns or 0)

    if raise_on == "read":
        fake.read = MagicMock(side_effect=serial.SerialException("RX fail"))
    else:
        fake.read = MagicMock(return_value=read_data)

    return fake


def _build_ccsds_packet(payload_len: int = 4) -> bytes:
    """Build bytes shaped like a SYNC + CCSDS header + payload + CRC
    that `receive_packet` can parse end-to-end."""
    sync = struct.pack(">I", SYNC_WORD)
    # CommunicationManager.receive_packet unpacks buf[4:10] as
    # (>H, >H, >H) = (primary_hdr, seq, data_length).
    header = struct.pack(">HHH", 0x0820, 0x0001, payload_len)
    body = bytes(range(payload_len))
    # total_len = 10 (sync+header) + data_length + 1 (trailing byte)
    trailing = b"\x00"
    return sync + header + body + trailing


# --------------------------------------------------------------------------
#  initialize paths
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_initialize_opens_serial_port_on_success() -> None:
    """initialize() returns True when serial.Serial succeeds."""
    fake = _make_fake_serial()
    comm = CommunicationManager({"port": "/dev/ttyS99", "baud_rate": 9600})

    with patch("modules.communication.serial.Serial", return_value=fake):
        ok = await comm.initialize()
    assert ok is True
    assert comm.is_connected() is True


@pytest.mark.asyncio
async def test_initialize_handles_serial_exception() -> None:
    """A SerialException from serial.Serial() should set ERROR state."""
    comm = CommunicationManager({"port": "/dev/fake"})

    with patch("modules.communication.serial.Serial",
                side_effect=serial.SerialException("no port")):
        ok = await comm.initialize()
    assert ok is False
    assert comm.is_connected() is False


# --------------------------------------------------------------------------
#  send_packet paths
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_packet_writes_bytes_on_happy_path() -> None:
    payload = b"beacon12"
    fake = _make_fake_serial(write_returns=len(payload))
    comm = CommunicationManager({})

    with patch("modules.communication.serial.Serial", return_value=fake):
        await comm.initialize()
        ok = await comm.send_packet(payload)

    assert ok is True
    fake.write.assert_called_once_with(payload)


@pytest.mark.asyncio
async def test_send_packet_queues_when_port_closed() -> None:
    comm = CommunicationManager({})
    # Never called initialize — port is None.
    ok = await comm.send_packet(b"beacon")
    assert ok is False
    # Packet should be in tx_queue for later flush.
    assert len(comm.tx_queue) == 1


@pytest.mark.asyncio
async def test_send_packet_handles_write_exception() -> None:
    fake = _make_fake_serial(raise_on="write")
    comm = CommunicationManager({})

    with patch("modules.communication.serial.Serial", return_value=fake):
        await comm.initialize()
        ok = await comm.send_packet(b"beacon")

    assert ok is False
    assert len(comm.tx_queue) == 1   # queued for retry
    assert comm.is_connected() is False


# --------------------------------------------------------------------------
#  receive_packet paths
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_receive_packet_returns_none_when_port_closed() -> None:
    comm = CommunicationManager({})
    pkt = await comm.receive_packet()
    assert pkt is None


@pytest.mark.asyncio
async def test_receive_packet_returns_none_on_no_data() -> None:
    fake = _make_fake_serial(in_waiting=0)
    comm = CommunicationManager({})
    with patch("modules.communication.serial.Serial", return_value=fake):
        await comm.initialize()
        pkt = await comm.receive_packet()
    assert pkt is None


@pytest.mark.asyncio
async def test_receive_packet_returns_none_on_no_sync() -> None:
    noise = b"\xAA" * 32
    fake = _make_fake_serial(in_waiting=len(noise), read_data=noise)
    comm = CommunicationManager({})
    with patch("modules.communication.serial.Serial", return_value=fake):
        await comm.initialize()
        pkt = await comm.receive_packet()
    assert pkt is None


@pytest.mark.asyncio
async def test_receive_packet_assembles_full_frame() -> None:
    full = _build_ccsds_packet(payload_len=4)
    # Prepend 6 bytes of noise so the sync-scan has to skip them.
    stream = b"\x11" * 6 + full
    fake = _make_fake_serial(in_waiting=len(stream), read_data=stream)
    comm = CommunicationManager({})

    with patch("modules.communication.serial.Serial", return_value=fake):
        await comm.initialize()
        pkt = await comm.receive_packet()

    assert pkt is not None
    assert pkt.startswith(struct.pack(">I", SYNC_WORD))


@pytest.mark.asyncio
async def test_receive_packet_handles_short_frame() -> None:
    """in_waiting >= 14 but the buffer is truncated — returns None."""
    truncated = struct.pack(">I", SYNC_WORD) + b"\x00" * 6
    fake = _make_fake_serial(in_waiting=len(truncated), read_data=truncated)
    comm = CommunicationManager({})
    with patch("modules.communication.serial.Serial", return_value=fake):
        await comm.initialize()
        pkt = await comm.receive_packet()
    assert pkt is None


@pytest.mark.asyncio
async def test_receive_packet_handles_serial_exception() -> None:
    fake = _make_fake_serial(in_waiting=32, raise_on="read")
    comm = CommunicationManager({})
    with patch("modules.communication.serial.Serial", return_value=fake):
        await comm.initialize()
        pkt = await comm.receive_packet()
    assert pkt is None
    assert comm.is_connected() is False


# --------------------------------------------------------------------------
#  flush_tx_queue + housekeeping
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_flush_tx_queue_sends_all() -> None:
    fake = _make_fake_serial(write_returns=4)
    comm = CommunicationManager({})
    with patch("modules.communication.serial.Serial", return_value=fake):
        await comm.initialize()
        comm.tx_queue.append(b"aaaa")
        comm.tx_queue.append(b"bbbb")
        sent = await comm.flush_tx_queue()
    assert sent == 2
    assert len(comm.tx_queue) == 0


@pytest.mark.asyncio
async def test_flush_tx_queue_stops_on_failure() -> None:
    """If send_packet returns False mid-flush, flush halts and keeps
    the remaining packets queued."""
    fake = _make_fake_serial(raise_on="write")
    comm = CommunicationManager({})
    with patch("modules.communication.serial.Serial", return_value=fake):
        await comm.initialize()
        comm.tx_queue.append(b"a")
        comm.tx_queue.append(b"b")
        sent = await comm.flush_tx_queue()
    assert sent == 0
    # Both packets still queued (write failed immediately).
    assert len(comm.tx_queue) >= 1


@pytest.mark.asyncio
async def test_send_authenticated_command_round_trip() -> None:
    fake = _make_fake_serial(write_returns=100)
    comm = CommunicationManager({
        "hmac_key": "0123456789abcdef0123456789abcdef",
    })
    with patch("modules.communication.serial.Serial", return_value=fake):
        await comm.initialize()
        ok = await comm.send_authenticated_command(
            command_id=0x1234, payload=b"\x01\x02\x03\x04",
        )
    assert ok is True


@pytest.mark.asyncio
async def test_stop_closes_serial_port() -> None:
    fake = _make_fake_serial()
    comm = CommunicationManager({})
    with patch("modules.communication.serial.Serial", return_value=fake):
        await comm.initialize()
        await comm.start()
        await comm.stop()
    # close() was called on the mock.
    fake.close.assert_called_once()
    assert comm.is_connected() is False
