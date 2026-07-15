#!/usr/bin/env python3
"""Tune the uncertainty/diversity weight using V2 development rows only.

This script is deliberately separate from the simulator-in-the-loop V4/V3
experiment. For each process corner, V2 target-corner rows are split into a
feature-only acquisition pool and a held-out development evaluation subset.
Labels are revealed from the acquisition pool only after selection. The weight
is chosen by the median area under the worst-cell delay-R2 learning curve.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.online_spice_corner_calibration import (  # noqa: E402
    CELLS,
    CORNERS,
    DEFAULT_PRIMARY,
    PROPOSED_STRATEGY,
    acquire,
    evaluate,
    load_spice_dataset,
    markdown_table,
)


DEFAULT_OUTDIR = PROJECT_ROOT / "results" / "corner_acquisition_weight_tuning"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tune corner-support acquisition weights on V2 only.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_PRIMARY)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--seeds", nargs="*", type=int, default=list(range(10)))
    parser.add_argument("--weights", nargs="*", type=float, default=[0.0, 0.25, 0.5, 0.75, 1.0])
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--max-support", type=int, default=24)
    parser.add_argument("--n-estimators", type=int, default=160)
    args = parser.parse_args()
    args.dataset = args.dataset if args.dataset.is_absolute() else PROJECT_ROOT / args.dataset
    args.outdir = args.outdir if args.outdir.is_absolute() else PROJECT_ROOT / args.outdir
    for weight in args.weights:
        if weight < 0.0 or weight > 1.0:
            parser.error("weights must lie in [0, 1]")
    return args


def development_split(
    data: pd.DataFrame,
    corner: str,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    base = data[data["corner"] != corner].copy().reset_index(drop=True)
    target = data[data["corner"] == corner].copy().reset_index(drop=True)
    pool, evaluation = train_test_split(
        target,
        train_size=0.60,
        random_state=seed + 20260711,
        stratify=target["cell_type"],
    )
    pool = pool.reset_index(drop=True)
    pool["candidate_id"] = np.arange(len(pool), dtype=int)
    evaluation = evaluation.reset_index(drop=True)
    return base, pool, evaluation


def run_weight(
    base: pd.DataFrame,
    pool: pd.DataFrame,
    evaluation: pd.DataFrame,
    corner: str,
    seed: int,
    weight: float,
    args: argparse.Namespace,
) -> pd.DataFrame:
    selected_ids: list[int] = []
    support = pool.iloc[0:0].copy()
    rows: list[dict[str, Any]] = []
    rng_seed = 700_000 + seed * 101 + CORNERS.index(corner) * 17 + int(round(weight * 100))

    while True:
        metrics, models = evaluate(
            base,
            support,
            evaluation,
            seed,
            args.n_estimators,
            top_fraction=0.20,
        )
        rows.append(
            {
                "seed": seed,
                "heldout_corner": corner,
                "uncertainty_weight": weight,
                "diversity_weight": 1.0 - weight,
                "support_rows": len(support),
                **metrics,
            }
        )
        if len(support) >= args.max_support:
            break
        rng = np.random.default_rng(rng_seed + len(support) * 1009)
        selected = acquire(
            PROPOSED_STRATEGY,
            pool,
            selected_ids,
            models,
            min(args.batch_size, args.max_support - len(support)),
            rng,
            uncertainty_weight=weight,
            diversity_weight=1.0 - weight,
        )
        revealed = pool[pool["candidate_id"].isin(selected["candidate_id"])].copy()
        support = pd.concat([support, revealed], ignore_index=True)
        selected_ids.extend(selected["candidate_id"].astype(int).tolist())
    return pd.DataFrame(rows)


def curve_area(group: pd.DataFrame, metric: str) -> float:
    ordered = group.sort_values("support_rows")
    x = ordered["support_rows"].to_numpy(dtype=float)
    y = ordered[metric].to_numpy(dtype=float)
    if len(x) < 2 or x[-1] <= x[0]:
        return float("nan")
    return float(np.trapezoid(y, x) / (x[-1] - x[0]))


def summarize(results: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    area_rows: list[dict[str, Any]] = []
    for (seed, corner, weight), group in results.groupby(
        ["seed", "heldout_corner", "uncertainty_weight"]
    ):
        area_rows.append(
            {
                "seed": seed,
                "heldout_corner": corner,
                "uncertainty_weight": weight,
                "diversity_weight": 1.0 - weight,
                "worst_cell_delay_r2_aulc": curve_area(group, "worst_cell_delay_r2"),
                "overall_delay_r2_aulc": curve_area(group, "delay_r2"),
                "top20_recall_aulc": curve_area(group, "top20_recall"),
            }
        )
    areas = pd.DataFrame(area_rows)
    summary = (
        areas.groupby(["uncertainty_weight", "diversity_weight"])
        .agg(
            runs=("seed", "count"),
            median_worst_cell_delay_r2_aulc=("worst_cell_delay_r2_aulc", "median"),
            q25_worst_cell_delay_r2_aulc=("worst_cell_delay_r2_aulc", lambda x: x.quantile(0.25)),
            q75_worst_cell_delay_r2_aulc=("worst_cell_delay_r2_aulc", lambda x: x.quantile(0.75)),
            median_overall_delay_r2_aulc=("overall_delay_r2_aulc", "median"),
            median_top20_recall_aulc=("top20_recall_aulc", "median"),
        )
        .reset_index()
        .sort_values(
            ["median_worst_cell_delay_r2_aulc", "median_overall_delay_r2_aulc"],
            ascending=False,
        )
    )
    return areas, summary


def main() -> int:
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    data = load_spice_dataset(args.dataset)
    result_parts: list[pd.DataFrame] = []
    for seed in args.seeds:
        for corner in CORNERS:
            base, pool, evaluation = development_split(data, corner, seed)
            if set(pool["cell_type"].unique()) != set(CELLS):
                raise ValueError("Development pool does not cover all cells")
            for weight in args.weights:
                result_parts.append(run_weight(base, pool, evaluation, corner, seed, weight, args))

    results = pd.concat(result_parts, ignore_index=True)
    areas, summary = summarize(results)
    best = summary.iloc[0]
    results.to_csv(args.outdir / "weight_tuning_trajectories.csv", index=False)
    areas.to_csv(args.outdir / "weight_tuning_curve_areas.csv", index=False)
    summary.to_csv(args.outdir / "weight_tuning_summary.csv", index=False)
    protocol = {
        "dataset": str(args.dataset),
        "validation_dataset_used": False,
        "seeds": args.seeds,
        "weights": args.weights,
        "selection_metric": "median_worst_cell_delay_r2_aulc",
        "selected_uncertainty_weight": float(best["uncertainty_weight"]),
        "selected_diversity_weight": float(best["diversity_weight"]),
    }
    (args.outdir / "selected_weight.json").write_text(
        json.dumps(protocol, indent=2) + "\n", encoding="utf-8"
    )
    report = [
        "# V2-Only Acquisition-Weight Tuning",
        "",
        "The independent V3 validation dataset was not used in this tuning step.",
        "The primary selection criterion was the median area under the worst-cell delay-R2 learning curve.",
        "",
        markdown_table(summary),
        "",
        f"Selected uncertainty weight: {best['uncertainty_weight']:.2f}",
        f"Selected diversity weight: {best['diversity_weight']:.2f}",
    ]
    (args.outdir / "weight_tuning_report.md").write_text(
        "\n".join(report) + "\n", encoding="utf-8"
    )
    print(f"Selected uncertainty weight: {best['uncertainty_weight']:.2f}")
    print(f"Selected diversity weight: {best['diversity_weight']:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
