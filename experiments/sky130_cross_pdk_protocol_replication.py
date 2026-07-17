#!/usr/bin/env python3
"""Replicate the locked GF180MCU online protocol on released SKY130 cells."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import qmc


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.library_online_external_validation import (  # noqa: E402
    FEATURES,
    balanced_space_filling_order,
    evaluate_pool,
)
from spice_v2.sky130_library_cells import (  # noqa: E402
    device_summary,
    selected_cells,
    simulate_library_point,
)


DEFAULT_ROOT = PROJECT_ROOT / "results" / "sky130_cross_pdk_replication"
DEFAULT_PRIMARY = DEFAULT_ROOT / "primary/sky130_library_primary.csv"
DEFAULT_VALIDATION = DEFAULT_ROOT / "validation/sky130_library_validation.csv"
DEFAULT_ONLINE = DEFAULT_ROOT / "online"
GF_STOPPING_PROTOCOL = (
    PROJECT_ROOT
    / "results/gf180_library_external_validation/online/stopping/stopping_protocol_and_results.json"
)
CORNER_SEQUENCE = ("typical", "ff", "ss")
EXPECTED_LOCKED_RULE = {
    "minimum_budget": 64,
    "prequential_nmae_threshold": 0.25,
    "prediction_change_threshold": 0.05,
    "coverage_ratio_threshold": 0.5,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--primary", type=Path, default=DEFAULT_PRIMARY)
    parser.add_argument("--validation", type=Path, default=DEFAULT_VALIDATION)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_ONLINE)
    parser.add_argument("--seeds", nargs="*", type=int, default=[0, 1, 2, 3, 4])
    parser.add_argument("--corners", nargs="*", default=list(CORNER_SEQUENCE))
    parser.add_argument("--drives", nargs="*", type=int, default=[1, 4])
    parser.add_argument("--candidate-per-variant", type=int, default=6)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--n-estimators", type=int, default=320)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--summarize-only", action="store_true")
    args = parser.parse_args()
    for name in ("primary", "validation", "outdir"):
        setattr(args, name, getattr(args, name).expanduser().resolve())
    return args


def load_dataset(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = set(FEATURES + ["delay_avg_ns", "power_avg_uW", "status", "fidelity"])
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{path} is missing columns: {missing}")
    frame = frame[
        frame["status"].eq("ok")
        & frame["fidelity"].eq("SPICE_SKY130_RELEASED_SPICE")
    ].copy()
    if frame.empty:
        raise ValueError(f"No released-cell SKY130 rows in {path}")
    return frame.reset_index(drop=True)


def candidate_pool(
    seed: int,
    corner: str,
    drives: tuple[int, ...],
    points_per_variant: int,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    cells = selected_cells(drives)
    corner_index = CORNER_SEQUENCE.index(corner)
    for cell_index, cell in enumerate(cells):
        sampler = qmc.LatinHypercube(
            d=4,
            seed=20260901 + seed * 1009 + corner_index * 137 + cell_index,
        )
        unit = sampler.random(n=points_per_variant)
        points = qmc.scale(
            unit,
            [1.62, -40.0, 0.02, 0.001],
            [1.98, 125.0, 12.0, 0.2059],
        )
        device = device_summary(cell)
        for vdd, temp, slew, cload in points:
            rows.append(
                {
                    "pdk": "SKY130",
                    "process_node_nm": 130,
                    "cell_family": cell.family.upper(),
                    "cell_variant": cell.variant.upper(),
                    "source_cell_variant": cell.source_variant.upper(),
                    "drive_strength": cell.drive,
                    "input_arc": cell.input_arc,
                    "inverting": int(cell.inverting),
                    "input_count": len(cell.signal_inputs),
                    **device,
                    "Vdd": float(vdd),
                    "Temp": float(temp),
                    "slew_ns": float(slew),
                    "Cload_pF": float(cload),
                    "corner": corner,
                    "seed": seed,
                    "heldout_corner": corner,
                }
            )
    frame = pd.DataFrame(rows)
    frame.insert(0, "candidate_id", np.arange(len(frame), dtype=int))
    return frame


def simulate_pool(
    pool: pd.DataFrame,
    order: list[int],
    args: argparse.Namespace,
    seed: int,
    corner: str,
) -> pd.DataFrame:
    run_dir = args.outdir / "runs" / f"seed_{seed}" / f"corner_{corner}"
    output = run_dir / "measured_pool_96.csv"
    if args.resume and output.exists():
        frame = pd.read_csv(output)
        if len(frame) == len(pool) and frame["status"].eq("ok").all():
            return frame.sort_values("query_order").reset_index(drop=True)
    run_dir.mkdir(parents=True, exist_ok=True)
    cells = {cell.variant.upper(): cell for cell in selected_cells(tuple(args.drives))}
    tasks = []
    for query_order, candidate_id in enumerate(order, start=1):
        candidate = pool.loc[pool["candidate_id"].eq(candidate_id)].iloc[0]
        cell = cells[str(candidate["cell_variant"])]
        sample_id = 15_000_000 + seed * 100_000 + CORNER_SEQUENCE.index(corner) * 10_000 + query_order
        tasks.append((query_order, candidate, cell, sample_id))

    rows = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {
            executor.submit(
                simulate_library_point,
                cell,
                sample_id,
                corner,
                float(candidate["Vdd"]),
                float(candidate["Temp"]),
                float(candidate["slew_ns"]),
                float(candidate["Cload_pF"]),
                run_dir / "netlists",
                run_dir / "logs",
            ): (query_order, candidate)
            for query_order, candidate, cell, sample_id in tasks
        }
        for future in as_completed(futures):
            query_order, candidate = futures[future]
            row = future.result()
            row.update(
                {
                    "candidate_id": int(candidate["candidate_id"]),
                    "seed": seed,
                    "heldout_corner": corner,
                    "query_order": query_order,
                    "batch_index": int(math.ceil(query_order / 16)),
                }
            )
            rows.append(row)
            print(
                f"SKY130 pool seed={seed} corner={corner} "
                f"{query_order}/{len(pool)} {row['status']}",
                flush=True,
            )
    frame = pd.DataFrame(rows).sort_values("query_order").reset_index(drop=True)
    frame.to_csv(output, index=False)
    if not frame["status"].eq("ok").all():
        raise RuntimeError(f"SPICE failures in {output}")
    return frame


def load_locked_rule() -> dict[str, float | int]:
    protocol = json.loads(GF_STOPPING_PROTOCOL.read_text(encoding="utf-8"))
    rule = protocol["locked_rule"]
    if rule != EXPECTED_LOCKED_RULE:
        raise ValueError(f"GF180MCU locked rule changed unexpectedly: {rule}")
    return rule


def stop_budget(run: pd.DataFrame, rule: dict[str, float | int]) -> int:
    ordered = run.sort_values("support_budget").reset_index(drop=True)
    eligible = (
        ordered["support_budget"].ge(int(rule["minimum_budget"]))
        & ordered["prequential_delay_nmae"].le(float(rule["prequential_nmae_threshold"]))
        & ordered["prediction_change_nmae"].le(float(rule["prediction_change_threshold"]))
        & ordered["coverage_radius_ratio"].le(float(rule["coverage_ratio_threshold"]))
    )
    consecutive = eligible & eligible.shift(1, fill_value=False)
    if consecutive.any():
        return int(ordered.loc[consecutive, "support_budget"].iloc[0])
    return int(ordered["support_budget"].max())


def stopping_rows(
    trajectory: pd.DataFrame,
    rule: dict[str, float | int],
    method: str,
    fixed_budget: int | None = None,
) -> pd.DataFrame:
    rows = []
    for (seed, corner), run in trajectory.groupby(["seed", "heldout_corner"]):
        budget = fixed_budget if fixed_budget is not None else stop_budget(run, rule)
        selected = run[run["support_budget"].eq(budget)].iloc[0]
        gap = float(selected["delay_r2_gap_to_full"])
        rows.append(
            {
                "method": method,
                "seed": int(seed),
                "heldout_corner": corner,
                "stop_budget": int(budget),
                "query_reduction_pct": 100.0 * (96 - int(budget)) / 96,
                "delay_r2": float(selected["delay_r2"]),
                "full_delay_r2": float(run.loc[run["support_budget"].eq(96), "delay_r2"].iloc[0]),
                "delay_r2_gap_to_full": gap,
                "gap_le_0p02": bool(gap <= 0.02),
                "gap_le_0p05": bool(gap <= 0.05),
                "worst_family_delay_r2": float(selected["worst_family_delay_r2"]),
                "worst_variant_delay_r2": float(selected["worst_variant_delay_r2"]),
            }
        )
    return pd.DataFrame(rows)


def summarize(rows: pd.DataFrame) -> dict[str, float | int]:
    return {
        "runs": int(len(rows)),
        "median_stop_budget": float(rows["stop_budget"].median()),
        "median_query_reduction_pct": float(rows["query_reduction_pct"].median()),
        "gap_le_0p02_rate": float(rows["gap_le_0p02"].mean()),
        "gap_le_0p05_rate": float(rows["gap_le_0p05"].mean()),
        "median_delay_r2_gap_to_full": float(rows["delay_r2_gap_to_full"].median()),
        "maximum_delay_r2_gap_to_full": float(rows["delay_r2_gap_to_full"].max()),
        "median_delay_r2": float(rows["delay_r2"].median()),
        "median_worst_family_delay_r2": float(rows["worst_family_delay_r2"].median()),
        "median_worst_variant_delay_r2": float(rows["worst_variant_delay_r2"].median()),
    }


def write_outputs(
    trajectory: pd.DataFrame,
    diagnostics: pd.DataFrame,
    pools: pd.DataFrame,
    outdir: Path,
) -> None:
    rule = load_locked_rule()
    locked = stopping_rows(trajectory, rule, "gf180_locked_rule")
    fixed48 = stopping_rows(trajectory, rule, "fixed_48", 48)
    fixed64 = stopping_rows(trajectory, rule, "fixed_64", 64)
    decisions = pd.concat([locked, fixed48, fixed64], ignore_index=True)
    comparison = {
        "gf180_locked_rule": summarize(locked),
        "fixed_48": summarize(fixed48),
        "fixed_64": summarize(fixed64),
    }
    summary = pd.DataFrame([{"method": key, **value} for key, value in comparison.items()])

    outdir.mkdir(parents=True, exist_ok=True)
    trajectory.to_csv(outdir / "sky130_online_trajectory.csv", index=False)
    diagnostics.to_csv(outdir / "sky130_online_internal_diagnostics.csv", index=False)
    pools.to_csv(outdir / "sky130_online_candidate_features.csv", index=False)
    decisions.to_csv(outdir / "sky130_stopping_decisions.csv", index=False)
    summary.to_csv(outdir / "sky130_stopping_summary.csv", index=False)
    protocol = {
        "study_role": "external cross-PDK protocol replication",
        "source_protocol": str(GF_STOPPING_PROTOCOL.relative_to(PROJECT_ROOT)),
        "locked_rule_selected_using_sky130": False,
        "locked_rule": rule,
        "cell_families": sorted(pools["cell_family"].unique().tolist()),
        "cell_variants": int(pools["cell_variant"].nunique()),
        "corners": list(CORNER_SEQUENCE),
        "seeds": sorted(int(seed) for seed in pools["seed"].unique()),
        "candidate_pool_size": 96,
        "validation_labels_visible_to_acquisition": False,
        "full_reference": "all 96 SKY130 candidate netlists measured with ngspice",
        "comparison": comparison,
    }
    (outdir / "sky130_cross_pdk_protocol_and_results.json").write_text(
        json.dumps(protocol, indent=2), encoding="utf-8"
    )
    result = comparison["gf180_locked_rule"]
    report = [
        "# SKY130 external cross-PDK protocol replication",
        "",
        "The stopping rule was copied unchanged from the GF180MCU development study. "
        "No SKY130 label or trajectory was used to select or tune its thresholds.",
        "",
        f"Locked rule: `{json.dumps(rule, sort_keys=True)}`.",
        "",
        f"- Independent pools: {result['runs']}.",
        f"- Median stop budget: {result['median_stop_budget']:.0f}/96.",
        f"- Median query reduction: {result['median_query_reduction_pct']:.1f}%.",
        f"- Gap <= 0.02 success rate: {result['gap_le_0p02_rate']:.3f}.",
        f"- Gap <= 0.05 success rate: {result['gap_le_0p05_rate']:.3f}.",
        f"- Median delay R2 gap to full reference: {result['median_delay_r2_gap_to_full']:.4f}.",
        f"- Maximum delay R2 gap to full reference: {result['maximum_delay_r2_gap_to_full']:.4f}.",
        "",
        "This is a protocol-replication result with PDK-specific retraining, not zero-shot "
        "transfer of a GF180MCU regression model to SKY130.",
    ]
    (outdir / "sky130_cross_pdk_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps(protocol, indent=2))


def main() -> int:
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    primary = load_dataset(args.primary)
    validation = load_dataset(args.validation)
    trajectories = []
    diagnostics = []
    pools = []
    for seed in args.seeds:
        for corner in args.corners:
            pool = candidate_pool(seed, corner, tuple(args.drives), args.candidate_per_variant)
            order = balanced_space_filling_order(pool)
            pool["query_order"] = pool["candidate_id"].map({cid: i + 1 for i, cid in enumerate(order)})
            pools.append(pool)
            measured_path = args.outdir / "runs" / f"seed_{seed}" / f"corner_{corner}/measured_pool_96.csv"
            if args.summarize_only:
                measured = pd.read_csv(measured_path)
            else:
                measured = simulate_pool(pool, order, args, seed, corner)
            trajectory, diagnostic = evaluate_pool(
                primary, validation, measured, seed, corner, args.n_estimators
            )
            trajectories.append(trajectory)
            diagnostics.append(diagnostic)
    write_outputs(
        pd.concat(trajectories, ignore_index=True),
        pd.concat(diagnostics, ignore_index=True),
        pd.concat(pools, ignore_index=True),
        args.outdir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
