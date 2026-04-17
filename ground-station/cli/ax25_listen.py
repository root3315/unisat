"""AX.25 listener over TCP loopback.

Acts as a TCP server: the firmware SITL shim connects as a client,
streams encoded bytes, the listener decodes them and prints one JSON
line per frame to stdout.

Usage:
  python -m cli.ax25_listen [--host 127.0.0.1] [--port 52100] [--count N]
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.ax25 import Ax25Decoder, AX25Error  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=52100)
    ap.add_argument("--count", type=int, default=0,
                    help="exit after N frames (0 = never)")
    args = ap.parse_args()

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((args.host, args.port))
    srv.listen(1)
    print(f"[ax25_listen] waiting on {args.host}:{args.port}",
          file=sys.stderr, flush=True)

    conn, peer = srv.accept()
    print(f"[ax25_listen] connected: {peer}", file=sys.stderr, flush=True)

    decoder = Ax25Decoder()
    frames_seen = 0
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            for b in data:
                try:
                    frame = decoder.push_byte(b)
                except AX25Error as e:
                    print(json.dumps({"error": str(e)}), flush=True)
                    continue
                if frame is None:
                    continue
                print(json.dumps({
                    "dst": {"callsign": frame.dst.callsign,
                            "ssid": frame.dst.ssid},
                    "src": {"callsign": frame.src.callsign,
                            "ssid": frame.src.ssid},
                    "pid": frame.pid,
                    "info_hex": frame.info.hex(),
                    "fcs_valid": frame.fcs_valid,
                }), flush=True)
                frames_seen += 1
                if args.count and frames_seen >= args.count:
                    return 0
    finally:
        conn.close()
        srv.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
