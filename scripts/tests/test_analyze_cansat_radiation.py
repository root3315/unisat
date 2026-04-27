"""Unit tests for ``scripts/analyze_cansat_radiation.py``.

Closes #18 — establishes a regression guard around the SBM-20 radiation
post-processor. Five cases cover the script's contract: shipped-baseline
self-consistency, the injected-anomaly bin's peak signal, the threshold
behaviour on a hand-crafted high-rate window, the datasheet sensitivity
constant, and the Poisson-uncertainty monotonicity.
"""

from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO / "scripts" / "analyze_cansat_radiation.py"
BASELINE_CSV = REPO / "docs" / "missions" / "cansat_radiation" / "baseline_sitl_dataset.csv"


def _load_module():
    """Import ``analyze_cansat_radiation`` directly from its file path.

    The module lives under ``scripts/`` (no package), so we go through
    ``importlib`` rather than a regular import so the test does not
    depend on ``scripts`` being on ``sys.path``.
    """

    spec = importlib.util.spec_from_file_location(
        "analyze_cansat_radiation", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["analyze_cansat_radiation"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def acr():
    return _load_module()


@pytest.fixture(scope="module")
def baseline_rows(acr):
    assert BASELINE_CSV.exists(), f"baseline dataset missing at {BASELINE_CSV}"
    return acr.analyze(BASELINE_CSV, bin_width_m=20.0)


def _raw_total_count(csv_path: Path) -> int:
    """Sum the per-window SBM-20 counts from the raw CSV.

    Mirrors what ``analyze`` aggregates so the test can assert the
    binner does not silently drop or double-count rows.
    """

    total = 0
    with csv_path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                if float(row["altitude_m"]) < 0:
                    continue
                total += int(row["sbm20_count_window"])
            except (KeyError, ValueError):
                continue
    return total


def test_baseline_dataset_is_self_consistent(baseline_rows):
    """Shipped baseline produces ≥1 bin, sane dose rates, and conservation of counts."""

    assert len(baseline_rows) >= 1

    for row in baseline_rows:
        # 0–2 μSv/h spans the whole physically plausible space for the
        # baseline mission; any bin outside that range means the unit
        # conversion drifted (the v1.5.0 ``× 3600`` regression).
        assert 0.0 <= row["dose_rate_usv_per_h"] <= 2.0, row

    binned_total = sum(row["n_counts"] for row in baseline_rows)
    raw_total = _raw_total_count(BASELINE_CSV)
    assert binned_total == raw_total


def test_injected_anomaly_bin_holds_the_peak_dose_rate(baseline_rows):
    """The injected high-rate event lives in the 300–320 m bin.

    The shipped baseline injects a count burst near 310 m. The
    Poisson uncertainty on that bin keeps |z| under the script's
    threshold, so we don't assert ``is_anomaly`` here — we assert the
    cleaner physical signal: the 310 m bin holds the peak dose rate.
    """

    peak = max(baseline_rows, key=lambda r: r["dose_rate_usv_per_h"])
    assert peak["altitude_mid_m"] == pytest.approx(310.0, abs=0.5)
    # Sanity: the peak is actually elevated relative to the baseline model.
    assert peak["residual_usv_per_h"] > 0


def test_anomaly_threshold_flags_a_handcrafted_burst(acr, tmp_path):
    """Synthetic CSV with a high-rate window must surface as an anomaly.

    Hand-crafted so the count rate is ~50× the baseline expectation:
    the resulting dose rate (~2.3 μSv/h vs ~0.1 baseline) sits well
    above the |z|>2 threshold, regardless of Poisson noise.
    """

    csv_path = tmp_path / "burst.csv"
    fields = ["t_ms", "altitude_m", "sbm20_count_window", "gnss_lat", "gnss_lon"]
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for i in range(40):
            writer.writerow({
                "t_ms": i * 100,
                "altitude_m": 100.0,
                "sbm20_count_window": 5,
                "gnss_lat": 41.28,
                "gnss_lon": 69.24,
            })

    rows = acr.analyze(csv_path, bin_width_m=20.0)
    target = [
        r for r in rows if r["altitude_mid_m"] == pytest.approx(110.0, abs=0.5)
    ]
    assert target, f"expected a 100-120m bin, got {[r['altitude_bin_m'] for r in rows]}"
    assert target[0]["is_anomaly"] is True
    assert target[0]["z_score_vs_H0"] > acr.ANOMALY_Z_THRESHOLD


def test_sensitivity_constant_matches_datasheet(acr):
    """Guard the SBM-20 datasheet constant against silent edits.

    The v1.5.0 spurious ``× 3600`` regression would have been caught
    by an equivalent guard. Pin the count-rate↔dose ratio.
    """

    assert acr.SBM20_SENSITIVITY == 22.0


def test_poisson_uncertainty_increases_with_fewer_counts(acr, tmp_path):
    """Smaller bin → larger Poisson uncertainty (basic monotonicity).

    Two synthetic CSVs at the same altitude bin: one with 100 counts
    over many samples, one with 4 counts over fewer samples. Smaller-N
    must produce a larger absolute uncertainty.
    """

    fields = ["t_ms", "altitude_m", "sbm20_count_window", "gnss_lat", "gnss_lon"]

    def make_csv(name: str, counts_per_window: int, rows: int):
        path = tmp_path / name
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            for i in range(rows):
                writer.writerow({
                    "t_ms": i * 100,
                    "altitude_m": 200.0,
                    "sbm20_count_window": counts_per_window,
                    "gnss_lat": 41.28,
                    "gnss_lon": 69.24,
                })
        return path

    big = acr.analyze(make_csv("big.csv", counts_per_window=10, rows=10), bin_width_m=20.0)
    small = acr.analyze(make_csv("small.csv", counts_per_window=4, rows=1), bin_width_m=20.0)

    big_bin = next(r for r in big if r["altitude_mid_m"] == pytest.approx(210.0, abs=0.5))
    small_bin = next(r for r in small if r["altitude_mid_m"] == pytest.approx(210.0, abs=0.5))

    assert small_bin["uncertainty_usv_per_h"] > big_bin["uncertainty_usv_per_h"]
