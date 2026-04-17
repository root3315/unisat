"""Send a single AX.25 UI frame over TCP loopback.

Acts as a TCP client connecting to ax25_listen's server socket (or
to the firmware SITL once both can cross-talk via a proxy).

Usage:
  python -m cli.ax25_send --dst-call CQ --dst-ssid 0 \\
      --src-call UN8SAT --src-ssid 1 --info-hex 68656c6c6f
"""

from __future__ import annotations

import argparse
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.ax25 import Address, encode_ui_frame  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=52100)
    ap.add_argument("--dst-call", required=True)
    ap.add_argument("--dst-ssid", type=int, default=0)
    ap.add_argument("--src-call", required=True)
    ap.add_argument("--src-ssid", type=int, default=0)
    ap.add_argument("--info-hex", default="")
    args = ap.parse_args()

    frame = encode_ui_frame(
        Address(args.dst_call, args.dst_ssid),
        Address(args.src_call, args.src_ssid),
        0xF0,
        bytes.fromhex(args.info_hex),
    )

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((args.host, args.port))
        s.sendall(frame)
    print(f"sent {len(frame)} bytes", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
