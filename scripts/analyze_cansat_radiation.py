#!/usr/bin/env python3
"""Analyze a CanSat radiation-mission flight CSV.

Reads an on-board flight log produced by UniSat's CanSat data logger
(see ``docs/missions/cansat_radiation/KEY_DATA_PACKET.md``), bins the
SBM-20 events by altitude, and detects anomalies relative to the
baseline UNSCEAR-derived model.

Usage:
    python scripts/analyze_cansat_radiation.py \\
        docs/missions/cansat_radiation/baseline_sitl_dataset.csv \\
        --output data/radiation_profile.csv \\
        --bin-width 20

If you want to try it before a real flight, point it at the baseline
SITL dataset shipped under docs/missions/cansat_radiation/.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path

# --- Model parameters --------------------------------------------------
# UNSCEAR 2020 mean terrestrial dose rate and vertical gradient
# (taken from the science mission doc for this project).
H0_BASELINE_USV = 0.10
H0_GRADIENT_USV_PER_M = 6e-5

# SBM-20 sensitivity from the datasheet (counts per second per μSv/h).
SBM20_SENSITIVITY = 22.0

ANOMALY_Z_THRESHOLD = 2.0


def baseline_model(altitude_m: float) -> float:
    """Return predicted dose rate (μSv/h) at a given altitude."""
    return H0_BASELINE_USV + H0_GRADIENT_USV_PER_M * altitude_m


def analyze(csv_path: Path, bin_width_m: float = 20.0) -> list[dict]:
    """Bin SBM-20 events by altitude and compute dose rate per bin."""
    bins: dict[int, dict] = {}
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                alt = float(row["altitude_m"])
                counts = int(row["sbm20_count_window"])
            except (KeyError, ValueError):
                continue
            if alt < 0:
                continue
            bin_id = int(alt // bin_width_m)
            b = bins.setdefault(bin_id, {
                "altitude_min": bin_id * bin_width_m,
                "altitude_max": (bin_id + 1) * bin_width_m,
                "n_counts": 0,
                "n_samples": 0,
                "gnss_lat_sum": 0.0,
                "gnss_lon_sum": 0.0,
            })
            b["n_counts"] += counts
            b["n_samples"] += 1
            try:
                b["gnss_lat_sum"] += float(row["gnss_lat"])
                b["gnss_lon_sum"] += float(row["gnss_lon"])
            except (KeyError, ValueError):
                pass

    # Convert each bin to a dose-rate estimate
    results: list[dict] = []
    for bin_id, b in sorted(bins.items()):
        if b["n_samples"] == 0:
            continue
        # Each sample is 1 cycle (100 ms in baseline SITL) — 10 samples = 1 s.
        window_s = b["n_samples"] * 0.1
        count_rate = b["n_counts"] / window_s if window_s > 0 else 0.0
        # Sensitivity is in counts·s⁻¹ per μSv/h, so dose [μSv/h] =
        # count_rate [counts/s] / SBM20_SENSITIVITY. No 3600 factor —
        # the /h is already baked into the sensitivity's definition.
        dose_rate = count_rate / SBM20_SENSITIVITY
        # Poisson uncertainty propagates as √N on the count total.
        sigma_counts = math.sqrt(max(b["n_counts"], 1))
        dose_sigma = (sigma_counts / window_s) / SBM20_SENSITIVITY
        altitude_mid = 0.5 * (b["altitude_min"] + b["altitude_max"])
        predicted = baseline_model(altitude_mid)
        z_score = (dose_rate - predicted) / dose_sigma if dose_sigma > 0 else 0.0
        results.append({
            "altitude_bin_m": f"{b['altitude_min']:.1f}-{b['altitude_max']:.1f}",
            "altitude_mid_m": round(altitude_mid, 1),
            "dose_rate_usv_per_h": round(dose_rate, 4),
            "uncertainty_usv_per_h": round(dose_sigma, 4),
            "baseline_usv_per_h": round(predicted, 4),
            "residual_usv_per_h": round(dose_rate - predicted, 4),
            "z_score_vs_H0": round(z_score, 2),
            "n_counts": b["n_counts"],
            "window_s": round(window_s, 2),
            "gnss_lat_mean": round(b["gnss_lat_sum"] / b["n_samples"], 7),
            "gnss_lon_mean": round(b["gnss_lon_sum"] / b["n_samples"], 7),
            "is_anomaly": abs(z_score) > ANOMALY_Z_THRESHOLD,
        })
    return results


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("flight_csv", type=Path,
                   help="Input flight log (see KEY_DATA_PACKET.md)")
    p.add_argument("--output", type=Path, default=None,
                   help="Where to write the radiation-profile CSV "
                        "(default: stdout)")
    p.add_argument("--bin-width", type=float, default=20.0,
                   help="Altitude bin width in metres (default 20)")
    p.add_argument("--anomalies-only", action="store_true",
                   help="Print only bins with |z-score| > 2")
    args = p.parse_args()

    if not args.flight_csv.exists():
        print(f"error: {args.flight_csv} not found", file=sys.stderr)
        return 2

    rows = analyze(args.flight_csv, bin_width_m=args.bin_width)
    if args.anomalies_only:
        rows = [r for r in rows if r["is_anomaly"]]

    if not rows:
        print("no bins produced — is the CSV empty or malformed?",
              file=sys.stderr)
        return 1

    fields = list(rows[0].keys())
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8", newline="") as out:
            writer = csv.DictWriter(out, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        print(f"wrote {len(rows)} bins -> {args.output}", file=sys.stderr)
    else:
        writer = csv.DictWriter(sys.stdout, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    # Summary line to stderr
    anomalies = [r for r in rows if r["is_anomaly"]]
    peak = max(rows, key=lambda r: r["dose_rate_usv_per_h"])
    print(
        f"[summary] {len(rows)} altitude bins · "
        f"{len(anomalies)} anomalies (|z|>2) · "
        f"peak {peak['dose_rate_usv_per_h']:.3f} μSv/h "
        f"at {peak['altitude_mid_m']:.0f} m "
        f"(z={peak['z_score_vs_H0']:.1f})",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
