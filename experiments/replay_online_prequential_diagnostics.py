#!/usr/bin/env python3
"""Replay query batches to measure validation-blind prequential errors.

For each cell-balanced space-filling run, the model is reconstructed using
only the primary non-target-corner rows and labels revealed before the current
batch. The selected batch is predicted before its labels are added. These
prequential errors are internal diagnostics because V3 labels are not used in
their calculation. V3 trajectory metrics are merged afterward only to test
whether the diagnostics track independent generalization quality.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.online_spice_corner_calibration import (  # noqa: E402
    DEFAULT_OUTDIR,
    DEFAULT_PRIMARY,
    FEATURES,
    PROPOSED_STRATEGY,
    TARGETS,
    fit_models,
    load_spice_dataset,
    markdown_table,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay online batches for prequential diagnostics.")
    parser.add_argument("--primary-dataset", type=Path, default=DEFAULT_PRIMARY)
    parser.add_argument("--online-outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--n-estimators", type=int, default=240)
    args = parser.parse_args()
    args.primary_dataset = (
        args.primary_dataset if args.primary_dataset.is_absolute() else PROJECT_ROOT / args.primary_dataset
    )
    args.online_outdir = (
        args.online_outdir if args.online_outdir.is_absolute() else PROJECT_ROOT / args.online_outdir
    )
    return args


def safe_mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    denominator = np.maximum(np.abs(actual), 1e-12)
    return float(np.mean(np.abs((actual - predicted) / denominator)) * 100.0)


def replay_run(
    query_path: Path,
    primary: pd.DataFrame,
    trajectory: pd.DataFrame,
    n_estimators: int,
) -> pd.DataFrame:
    queries = pd.read_csv(query_path).sort_values("query_order")
    seed = int(queries["pool_seed"].iloc[0])
    corner = str(queries["heldout_corner"].iloc[0])
    base = primary[primary["corner"] != corner].copy().reset_index(drop=True)
    support = queries.iloc[0:0].copy()
    rows: list[dict[str, Any]] = []

    for batch_index, batch in queries.groupby("batch_index", sort=True):
        train = pd.concat([base, support], ignore_index=True)
        models = fit_models(train, seed, n_estimators)
        predictions = {target: models[target].predict(batch[FEATURES]) for target in TARGETS}
        delay_actual = batch["delay_avg_ns"].to_numpy(dtype=float)
        power_actual = batch["power_avg_uW"].to_numpy(dtype=float)
        delay_pred = predictions["delay_avg_ns"]
        power_pred = predictions["power_avg_uW"]

        support = pd.concat([support, batch], ignore_index=True)
        budget = len(support)
        external = trajectory[
            (trajectory["seed"] == seed)
            & (trajectory["heldout_corner"] == corner)
            & (trajectory["strategy"] == PROPOSED_STRATEGY)
            & (trajectory["spice_queries"] == budget)
        ]
        if len(external) != 1:
            raise ValueError(f"Expected one external row for seed={seed}, corner={corner}, budget={budget}")
        external_row = external.iloc[0]
        rows.append(
            {
                "seed": seed,
                "heldout_corner": corner,
                "strategy": PROPOSED_STRATEGY,
                "batch_index": int(batch_index),
                "support_budget": budget,
                "batch_rows": len(batch),
                "prequential_delay_mae_ns": float(np.mean(np.abs(delay_actual - delay_pred))),
                "prequential_delay_mape_pct": safe_mape(delay_actual, delay_pred),
                "prequential_power_mae_uW": float(np.mean(np.abs(power_actual - power_pred))),
                "prequential_power_mape_pct": safe_mape(power_actual, power_pred),
                "external_delay_r2": float(external_row["delay_r2"]),
                "external_worst_cell_delay_r2": float(external_row["worst_cell_delay_r2"]),
                "external_top20_recall": float(external_row["top20_recall"]),
            }
        )
    return pd.DataFrame(rows)


def correlation_table(diagnostics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    internal_metrics = [
        "prequential_delay_mae_ns",
        "prequential_delay_mape_pct",
        "prequential_power_mae_uW",
    ]
    external_metrics = ["external_delay_r2", "external_worst_cell_delay_r2"]
    for internal in internal_metrics:
        for external in external_metrics:
            result = spearmanr(diagnostics[internal], diagnostics[external])
            rows.append(
                {
                    "internal_metric": internal,
                    "external_metric": external,
                    "pairs": len(diagnostics),
                    "spearman_rho": float(result.statistic),
                    "p_value": float(result.pvalue),
                }
            )
    return pd.DataFrame(rows)


def main() -> int:
    args = parse_args()
    primary = load_spice_dataset(args.primary_dataset)
    trajectory = pd.read_csv(args.online_outdir / "online_spice_trajectory.csv")
    query_paths = sorted(
        (args.online_outdir / "runs").glob(
            f"seed_*/corner_*/{PROPOSED_STRATEGY}/queries.csv"
        )
    )
    if not query_paths:
        raise FileNotFoundError("No proposed-strategy query files were found")
    diagnostics = pd.concat(
        [replay_run(path, primary, trajectory, args.n_estimators) for path in query_paths],
        ignore_index=True,
    )
    diagnostics["rolling_two_batch_delay_mae_ns"] = (
        diagnostics.groupby(["seed", "heldout_corner"])["prequential_delay_mae_ns"]
        .transform(lambda values: values.rolling(2, min_periods=1).median())
    )
    correlations = correlation_table(diagnostics)
    diagnostics.to_csv(args.online_outdir / "online_spice_prequential_diagnostics.csv", index=False)
    correlations.to_csv(args.online_outdir / "online_spice_prequential_correlations.csv", index=False)

    compact = (
        diagnostics.groupby(["heldout_corner", "support_budget"])
        .agg(
            runs=("seed", "count"),
            median_prequential_delay_mae_ns=("prequential_delay_mae_ns", "median"),
            median_rolling_delay_mae_ns=("rolling_two_batch_delay_mae_ns", "median"),
            median_external_delay_r2=("external_delay_r2", "median"),
            median_external_worst_cell_delay_r2=("external_worst_cell_delay_r2", "median"),
        )
        .reset_index()
    )
    report = [
        "# Validation-Blind Prequential Diagnostics",
        "",
        "Each batch was predicted before its SPICE labels were added. V3 labels were merged only after replay to assess diagnostic validity.",
        "",
        "## Budget Summary",
        "",
        markdown_table(compact),
        "",
        "## Correlation With Independent V3 Performance",
        "",
        markdown_table(correlations),
    ]
    (args.online_outdir / "online_spice_prequential_report.md").write_text(
        "\n".join(report) + "\n", encoding="utf-8"
    )
    metadata = {
        "strategy": PROPOSED_STRATEGY,
        "runs": len(query_paths),
        "batches": int(len(diagnostics)),
        "n_estimators": args.n_estimators,
        "v3_used_in_diagnostic": False,
        "v3_used_afterward_for_correlation_only": True,
    }
    (args.online_outdir / "online_spice_prequential_protocol.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Replayed {len(query_paths)} runs and {len(diagnostics)} batches")
    print(correlations.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
