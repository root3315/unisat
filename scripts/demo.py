"""End-to-end SITL demo.

Starts the ground-station ax25_listen server, then launches the C
sitl_fw binary which connects as a TCP client and transmits two
AX.25 UI beacon frames. The listener decodes them and prints JSON.
This script reads the JSON and exits 0 if both beacons arrived
with fcs_valid=true.

Usage:  python scripts/demo.py [--port 52100]
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GS = REPO / "ground-station"
FW_BIN = REPO / "firmware" / "build" / "sitl_fw"
if os.name == "nt":
    FW_BIN = FW_BIN.with_suffix(".exe")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=52100)
    ap.add_argument("--timeout", type=float, default=15.0)
    args = ap.parse_args()

    if not FW_BIN.exists():
        print(
            f"[demo] missing firmware binary: {FW_BIN}\n"
            f"       run 'cd firmware && cmake -B build && "
            f"cmake --build build --target sitl_fw' first.",
            file=sys.stderr,
        )
        return 2

    listener = subprocess.Popen(
        [sys.executable, "-m", "cli.ax25_listen",
         "--port", str(args.port), "--count", "2"],
        cwd=str(GS),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    time.sleep(0.5)  # give the TCP server a chance to bind

    fw = subprocess.Popen([str(FW_BIN), str(args.port)])

    frames = []
    deadline = time.time() + args.timeout
    try:
        while time.time() < deadline and len(frames) < 2:
            line = listener.stdout.readline()
            if not line:
                break
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("fcs_valid") is True:
                frames.append(obj)
                print(
                    f"[demo] beacon {len(frames)}: "
                    f"{obj['info_hex'][:32]}...",
                    flush=True,
                )
    finally:
        for proc in (fw, listener):
            if proc.poll() is None:
                if os.name == "nt":
                    proc.terminate()
                else:
                    proc.send_signal(signal.SIGTERM)
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()

    if len(frames) >= 2:
        print("[demo] SUCCESS — 2 beacons decoded")
        return 0
    print(f"[demo] FAIL — decoded {len(frames)} beacons", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
