#!/usr/bin/env python3
"""Cross-check released Liberty timing surfaces with fresh ngspice/CDL runs."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.metrics import mean_absolute_error, r2_score


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from spice_v2.gf180_library_cells import CELL_ROOT, LibraryCell, selected_cells, simulate_library_point  # noqa: E402


DEFAULT_OUTDIR = PROJECT_ROOT / "results" / "gf180_library_external_validation" / "liberty_crosscheck"
PVT = {
    "typical": ("tt_025C_1v80", 1.80, 25.0),
    "ff": ("ff_n40C_1v98", 1.98, -40.0),
    "ss": ("ss_125C_1v62", 1.62, 125.0),
}
GRID_INDICES = (0, 4, 9)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--drives", nargs="*", type=int, default=[1, 4])
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    args.outdir = args.outdir.expanduser().resolve()
    return args


def condition_matches(expression: str | None, fixed: dict[str, int]) -> bool:
    if not expression:
        return True
    terms = expression.replace("(", "").replace(")", "").split("&")
    for term in terms:
        token = term.strip()
        if not token:
            continue
        negated = token.startswith("!")
        pin = token[1:] if negated else token
        if pin not in fixed:
            return False
        desired = 0 if negated else 1
        if fixed[pin] != desired:
            return False
    return True


def liberty_json_path(cell: LibraryCell, pvt_suffix: str) -> Path:
    return CELL_ROOT / cell.family / f"{cell.subckt}__{pvt_suffix}.lib.json"


def select_timing_arc(cell: LibraryCell, data: dict[str, Any]) -> dict[str, Any]:
    root = next(iter(data.values()))
    output = root[f"pin {cell.output_pin}"]
    timing = output["timing "]
    arcs = timing if isinstance(timing, list) else [timing]
    expected_sense = "negative_unate" if cell.inverting else "positive_unate"
    fixed = dict(cell.fixed_inputs)
    matches = [
        arc
        for arc in arcs
        if arc.get("related_pin") == cell.active_pin
        and arc.get("timing_sense") == expected_sense
        and condition_matches(arc.get("when"), fixed)
    ]
    if not matches:
        matches = [
            arc
            for arc in arcs
            if arc.get("related_pin") == cell.active_pin and arc.get("timing_sense") == expected_sense
        ]
    if not matches:
        raise ValueError(f"No Liberty timing arc for {cell.variant} {cell.input_arc}")
    conditioned = [arc for arc in matches if arc.get("when")]
    return conditioned[0] if conditioned else matches[0]


def table(arc: dict[str, Any], prefix: str) -> dict[str, Any]:
    key = next(key for key in arc if key.startswith(prefix + " "))
    return arc[key]


def reference_points(cell: LibraryCell, corner: str) -> list[dict[str, Any]]:
    suffix, vdd, temp = PVT[corner]
    path = liberty_json_path(cell, suffix)
    data = json.loads(path.read_text(encoding="utf-8"))
    arc = select_timing_arc(cell, data)
    rise = table(arc, "cell_rise")
    fall = table(arc, "cell_fall")
    slew = np.asarray(rise["index_1"], dtype=float)
    load = np.asarray(rise["index_2"], dtype=float)
    rise_values = np.asarray(rise["values"], dtype=float)
    fall_values = np.asarray(fall["values"], dtype=float)
    rows = []
    for i in GRID_INDICES:
        for j in GRID_INDICES:
            rows.append(
                {
                    "cell": cell,
                    "corner": corner,
                    "Vdd": vdd,
                    "Temp": temp,
                    "slew_ns": float(slew[i]),
                    "Cload_pF": float(load[j]),
                    "liberty_cell_rise_ns": float(rise_values[i, j]),
                    "liberty_cell_fall_ns": float(fall_values[i, j]),
                    "liberty_delay_avg_ns": float((rise_values[i, j] + fall_values[i, j]) * 0.5),
                    "liberty_json_path": str(path.relative_to(PROJECT_ROOT)),
                    "liberty_when": arc.get("when", ""),
                    "liberty_timing_sense": arc.get("timing_sense", ""),
                }
            )
    return rows


def metric_row(group: pd.DataFrame, label: str, value: str) -> dict[str, Any]:
    actual = group["liberty_delay_avg_ns"].to_numpy(dtype=float)
    measured = group["delay_avg_ns"].to_numpy(dtype=float)
    denom = np.maximum(np.abs(actual), 1e-12)
    return {
        "group": label,
        "value": value,
        "points": len(group),
        "pearson_r": float(pearsonr(actual, measured).statistic),
        "spearman_rho": float(spearmanr(actual, measured).statistic),
        "r2": float(r2_score(actual, measured)),
        "mae_ns": float(mean_absolute_error(actual, measured)),
        "median_absolute_percentage_error": float(np.median(np.abs(measured - actual) / denom) * 100.0),
        "median_spice_to_liberty_ratio": float(np.median(measured / denom)),
    }


def main() -> int:
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    output = args.outdir / "liberty_spice_point_comparison.csv"
    if args.resume and output.exists():
        frame = pd.read_csv(output)
    else:
        references = []
        for cell in selected_cells(tuple(args.drives)):
            for corner in PVT:
                references.extend(reference_points(cell, corner))
        tasks = []
        for sample_offset, reference in enumerate(references):
            sample_id = 12_000_000 + sample_offset
            tasks.append((sample_id, reference))
        rows = []
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
            futures = {
                executor.submit(
                    simulate_library_point,
                    reference["cell"],
                    sample_id,
                    reference["corner"],
                    reference["Vdd"],
                    reference["Temp"],
                    reference["slew_ns"],
                    reference["Cload_pF"],
                    args.outdir / "netlists",
                    args.outdir / "logs",
                ): reference
                for sample_id, reference in tasks
            }
            for future in as_completed(futures):
                reference = futures[future]
                measured = future.result()
                cell = reference["cell"]
                row = {key: value for key, value in reference.items() if key != "cell"}
                row.update(measured)
                row["cell_family"] = cell.family.upper()
                row["cell_variant"] = cell.variant.upper()
                rows.append(row)
                print(f"Liberty check {cell.variant} {reference['corner']} {measured['status']}", flush=True)
        frame = pd.DataFrame(rows).sort_values(["cell_variant", "corner", "slew_ns", "Cload_pF"])
        frame.to_csv(output, index=False)
    successful = frame[frame["status"].eq("ok")].copy()
    if len(successful) != len(frame):
        raise RuntimeError(f"{len(frame) - len(successful)} Liberty cross-check simulations failed")
    metrics = [metric_row(successful, "all", "all")]
    for corner, group in successful.groupby("corner"):
        metrics.append(metric_row(group, "corner", str(corner)))
    for family, group in successful.groupby("cell_family"):
        metrics.append(metric_row(group, "cell_family", str(family)))
    metric_frame = pd.DataFrame(metrics)
    metric_frame.to_csv(args.outdir / "liberty_spice_agreement_metrics.csv", index=False)
    overall = metric_frame.iloc[0]
    report = [
        "# Released Liberty surface cross-check",
        "",
        "This is a partial compatibility check, not complete Liberty characterization. "
        "For each released cell variant and PVT file, nine low/mid/high slew-load points were re-simulated from the released CDL with ngspice.",
        "",
        f"- Successful point comparisons: {len(successful)}.",
        f"- Overall Spearman rho: {overall['spearman_rho']:.4f}.",
        f"- Overall Pearson r: {overall['pearson_r']:.4f}.",
        f"- Overall median absolute percentage error: {overall['median_absolute_percentage_error']:.2f}%.",
        f"- Median SPICE-to-Liberty delay ratio: {overall['median_spice_to_liberty_ratio']:.3f}.",
        "",
        "Absolute agreement is not assumed because the released characterization deck, waveform definitions, and parasitic assumptions are not available in the open library. Rank agreement is therefore reported separately from absolute error.",
    ]
    (args.outdir / "liberty_surface_crosscheck_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(metric_frame.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
