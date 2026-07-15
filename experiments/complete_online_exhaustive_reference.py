#!/usr/bin/env python3
"""Complete and evaluate the 96-point exhaustive online-pool references.

The five online strategies jointly cover most V4 candidates. This script runs
ngspice only for candidates that were never queried by any strategy, then keeps
one measured row per candidate to form an exhaustive 96-query reference for
each seed and held-out corner. It reports measured serial-equivalent runtime
and V3 performance for the full support pool, enabling direct comparisons with
the 24- and 48-query online budgets.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import sys
import time
from types import SimpleNamespace
from typing import Any

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.online_spice_corner_calibration import (  # noqa: E402
    CORNERS,
    DEFAULT_OUTDIR,
    DEFAULT_PRIMARY,
    DEFAULT_VALIDATION,
    PROPOSED_STRATEGY,
    evaluate,
    load_spice_dataset,
    markdown_table,
    row_to_sample,
)
from spice_v2.generate_spice_dataset import (  # noqa: E402
    DEFAULT_PDK_ROOT,
    find_model_file,
    result_row,
    run_ngspice,
    write_netlist,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Complete exhaustive V4 reference pools.")
    parser.add_argument("--primary-dataset", type=Path, default=DEFAULT_PRIMARY)
    parser.add_argument("--validation-dataset", type=Path, default=DEFAULT_VALIDATION)
    parser.add_argument("--online-outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--pdk-root", type=Path, default=DEFAULT_PDK_ROOT)
    parser.add_argument("--model-file", type=Path, default=None)
    parser.add_argument("--nmos-model", default="nmos_3p3")
    parser.add_argument("--pmos-model", default="pmos_3p3")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--n-estimators", type=int, default=240)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    for attribute in ["primary_dataset", "validation_dataset", "online_outdir", "pdk_root"]:
        path = Path(getattr(args, attribute)).expanduser()
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        setattr(args, attribute, path.resolve())
    if args.model_file is not None:
        path = Path(args.model_file).expanduser()
        args.model_file = (path if path.is_absolute() else PROJECT_ROOT / path).resolve()
    return args


def reference_sample_id(seed: int, corner: str, candidate_id: int) -> int:
    return 6_000_000 + seed * 100_000 + CORNERS.index(corner) * 10_000 + candidate_id


def simulate_missing(
    candidate: pd.Series,
    seed: int,
    corner: str,
    model_file: Path,
    run_dir: Path,
    args: argparse.Namespace,
) -> dict[str, Any]:
    sample_id = reference_sample_id(seed, corner, int(candidate["candidate_id"]))
    sample = row_to_sample(candidate, sample_id)
    generator_args = SimpleNamespace(
        netlist_dir=run_dir / "netlists",
        log_dir=run_dir / "logs",
        allow_generic_debug_models=False,
        nmos_model=args.nmos_model,
        pmos_model=args.pmos_model,
        statistical_mode="off",
        seed=seed,
        dry_run=False,
    )
    started = time.perf_counter()
    netlist_path = write_netlist(sample, model_file, generator_args)
    returncode, measurements, log_path = run_ngspice(
        netlist_path, sample, model_file, generator_args.log_dir
    )
    wall_time = time.perf_counter() - started
    row = result_row(
        sample,
        netlist_path,
        log_path,
        model_file,
        measurements,
        returncode,
        generator_args,
    )
    row.update(
        {
            "candidate_id": int(candidate["candidate_id"]),
            "seed": seed,
            "pool_seed": seed,
            "heldout_corner": corner,
            "strategy": "exhaustive_reference_completion",
            "spice_wall_time_s": wall_time,
            "reference_origin": "new_completion_query",
        }
    )
    return row


def complete_group(
    pool: pd.DataFrame,
    existing: pd.DataFrame,
    seed: int,
    corner: str,
    model_file: Path,
    args: argparse.Namespace,
) -> pd.DataFrame:
    reference_dir = args.online_outdir / "exhaustive_reference" / f"seed_{seed}" / f"corner_{corner}"
    completion_path = reference_dir / "completion_queries.csv"
    reference_dir.mkdir(parents=True, exist_ok=True)
    if args.resume and completion_path.exists():
        completed = pd.read_csv(completion_path)
    else:
        completed = pd.DataFrame()

    existing_ids = set(existing["candidate_id"].astype(int).tolist())
    completed_ids = set(completed["candidate_id"].astype(int).tolist()) if not completed.empty else set()
    missing = pool[
        ~pool["candidate_id"].astype(int).isin(existing_ids | completed_ids)
    ].copy()
    if not missing.empty:
        rows: list[dict[str, Any]] = []
        workers = max(1, min(args.workers, len(missing)))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(
                    simulate_missing,
                    candidate,
                    seed,
                    corner,
                    model_file,
                    reference_dir,
                    args,
                )
                for _, candidate in missing.iterrows()
            ]
            for future in as_completed(futures):
                rows.append(future.result())
        completed = pd.concat([completed, pd.DataFrame(rows)], ignore_index=True)
        completed.to_csv(completion_path, index=False)

    existing_one = (
        existing.sort_values(["candidate_id", "strategy"])
        .drop_duplicates("candidate_id", keep="first")
        .copy()
    )
    existing_one["reference_origin"] = "existing_online_query"
    reference = pd.concat([existing_one, completed], ignore_index=True)
    reference = reference.sort_values("candidate_id").drop_duplicates("candidate_id", keep="first")
    expected = set(pool["candidate_id"].astype(int))
    observed = set(reference["candidate_id"].astype(int))
    if observed != expected:
        raise ValueError(f"Reference pool incomplete for seed={seed}, corner={corner}")
    if not (reference["status"] == "ok").all():
        raise ValueError(f"Reference pool contains failed SPICE rows for seed={seed}, corner={corner}")
    reference.to_csv(reference_dir / "exhaustive_reference_96.csv", index=False)
    return reference


def duplicate_consistency(queries: pd.DataFrame) -> pd.DataFrame:
    grouped = queries.groupby(["seed", "heldout_corner", "candidate_id"])
    audit = grouped.agg(
        repeats=("strategy", "count"),
        delay_span_ns=("delay_avg_ns", lambda values: float(values.max() - values.min())),
        power_span_uW=("power_avg_uW", lambda values: float(values.max() - values.min())),
    ).reset_index()
    return audit[audit["repeats"] > 1].copy()


def evaluate_references(
    references: pd.DataFrame,
    primary: pd.DataFrame,
    validation: pd.DataFrame,
    trajectory: pd.DataFrame,
    n_estimators: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    metric_rows: list[dict[str, Any]] = []
    comparison_rows: list[dict[str, Any]] = []
    for (seed, corner), reference in references.groupby(["seed", "heldout_corner"]):
        base = primary[primary["corner"] != corner].copy()
        target_validation = validation[validation["corner"] == corner].copy()
        metrics, _ = evaluate(
            base,
            reference,
            target_validation,
            int(seed),
            n_estimators,
            top_fraction=0.20,
        )
        full_runtime = float(reference["spice_wall_time_s"].sum())
        metric_rows.append(
            {
                "seed": int(seed),
                "heldout_corner": corner,
                "support_rows": len(reference),
                "measured_spice_wall_time_s": full_runtime,
                **metrics,
            }
        )
        for budget in [24, 48]:
            online = trajectory[
                (trajectory["seed"] == seed)
                & (trajectory["heldout_corner"] == corner)
                & (trajectory["strategy"] == PROPOSED_STRATEGY)
                & (trajectory["spice_queries"] == budget)
            ]
            if len(online) != 1:
                raise ValueError("Missing proposed-strategy trajectory row")
            row = online.iloc[0]
            comparison_rows.append(
                {
                    "seed": int(seed),
                    "heldout_corner": corner,
                    "online_budget": budget,
                    "full_reference_queries": len(reference),
                    "query_reduction_pct": 100.0 * (len(reference) - budget) / len(reference),
                    "online_measured_wall_time_s": float(row["cumulative_spice_wall_time_s"]),
                    "full_measured_wall_time_s": full_runtime,
                    "measured_time_reduction_pct": 100.0
                    * (full_runtime - float(row["cumulative_spice_wall_time_s"]))
                    / full_runtime,
                    "online_delay_r2": float(row["delay_r2"]),
                    "full_delay_r2": float(metrics["delay_r2"]),
                    "delay_r2_gap_to_full": float(metrics["delay_r2"] - row["delay_r2"]),
                    "online_worst_cell_delay_r2": float(row["worst_cell_delay_r2"]),
                    "full_worst_cell_delay_r2": float(metrics["worst_cell_delay_r2"]),
                    "online_top20_recall": float(row["top20_recall"]),
                    "full_top20_recall": float(metrics["top20_recall"]),
                }
            )
    return pd.DataFrame(metric_rows), pd.DataFrame(comparison_rows)


def main() -> int:
    args = parse_args()
    model_file = find_model_file(args.pdk_root, args.model_file)
    if model_file is None or not model_file.exists():
        raise FileNotFoundError("A real GF180MCU model file is required")
    primary = load_spice_dataset(args.primary_dataset)
    validation = load_spice_dataset(args.validation_dataset)
    pools = pd.read_csv(args.online_outdir / "online_candidate_pool_features.csv")
    queries = pd.read_csv(args.online_outdir / "online_spice_queries.csv")
    trajectory = pd.read_csv(args.online_outdir / "online_spice_trajectory.csv")

    audit = duplicate_consistency(queries)
    audit.to_csv(args.online_outdir / "online_spice_duplicate_query_consistency.csv", index=False)
    if not audit.empty:
        if audit["delay_span_ns"].max() > 1e-12 or audit["power_span_uW"].max() > 1e-9:
            raise ValueError("Repeated candidate simulations are not numerically consistent")

    references: list[pd.DataFrame] = []
    for (seed, corner), pool in pools.groupby(["pool_seed", "heldout_corner"]):
        existing = queries[
            (queries["seed"] == seed) & (queries["heldout_corner"] == corner)
        ].copy()
        reference = complete_group(
            pool,
            existing,
            int(seed),
            str(corner),
            model_file,
            args,
        )
        references.append(reference)
        print(
            f"seed={seed} corner={corner} exhaustive_rows={len(reference)}",
            flush=True,
        )

    reference_all = pd.concat(references, ignore_index=True)
    metrics, comparison = evaluate_references(
        reference_all, primary, validation, trajectory, args.n_estimators
    )
    reference_all.to_csv(args.online_outdir / "online_spice_exhaustive_reference.csv", index=False)
    metrics.to_csv(args.online_outdir / "online_spice_exhaustive_reference_metrics.csv", index=False)
    comparison.to_csv(args.online_outdir / "online_spice_budget_vs_exhaustive.csv", index=False)

    compact = (
        comparison.groupby("online_budget")
        .agg(
            runs=("seed", "count"),
            median_query_reduction_pct=("query_reduction_pct", "median"),
            median_measured_time_reduction_pct=("measured_time_reduction_pct", "median"),
            median_online_delay_r2=("online_delay_r2", "median"),
            median_full_delay_r2=("full_delay_r2", "median"),
            median_delay_r2_gap_to_full=("delay_r2_gap_to_full", "median"),
            median_online_worst_cell_delay_r2=("online_worst_cell_delay_r2", "median"),
            median_full_worst_cell_delay_r2=("full_worst_cell_delay_r2", "median"),
            median_online_top20_recall=("online_top20_recall", "median"),
            median_full_top20_recall=("full_top20_recall", "median"),
        )
        .reset_index()
    )
    report = [
        "# Measured Exhaustive-Pool Reference",
        "",
        f"Completed {len(reference_all)} unique V4 candidate simulations across {len(metrics)} seed-corner pools.",
        "Repeated candidate simulations from different strategies were numerically audited before one row per candidate was retained.",
        "",
        "## Online Budgets Versus the 96-Query Reference",
        "",
        markdown_table(compact),
        "",
        "## Full Reference Metrics",
        "",
        markdown_table(metrics),
    ]
    (args.online_outdir / "online_spice_exhaustive_reference_report.md").write_text(
        "\n".join(report) + "\n", encoding="utf-8"
    )
    print(compact.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
