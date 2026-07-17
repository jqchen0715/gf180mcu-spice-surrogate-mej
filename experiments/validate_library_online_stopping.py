#!/usr/bin/env python3
"""Lock an observable stopping rule on development pools and test it blindly."""

from __future__ import annotations

from itertools import product
import json
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROOT = PROJECT_ROOT / "results" / "gf180_library_external_validation" / "online"
TRAJECTORY = ROOT / "library_online_trajectory.csv"
OUTPUT = ROOT / "stopping"
DEVELOPMENT_SEEDS = {0, 1, 2}
CONFIRMATION_SEEDS = {3, 4}


def stop_budget(run: pd.DataFrame, minimum: int, preq: float, change: float, coverage: float) -> int:
    ordered = run.sort_values("support_budget").reset_index(drop=True)
    eligible = (
        ordered["support_budget"].ge(minimum)
        & ordered["prequential_delay_nmae"].le(preq)
        & ordered["prediction_change_nmae"].le(change)
        & ordered["coverage_radius_ratio"].le(coverage)
    )
    consecutive = eligible & eligible.shift(1, fill_value=False)
    if consecutive.any():
        return int(ordered.loc[consecutive, "support_budget"].iloc[0])
    return int(ordered["support_budget"].max())


def apply_rule(frame: pd.DataFrame, rule: dict[str, float | int], split: str) -> pd.DataFrame:
    rows = []
    for (seed, corner), run in frame.groupby(["seed", "heldout_corner"]):
        budget = stop_budget(
            run,
            int(rule["minimum_budget"]),
            float(rule["prequential_nmae_threshold"]),
            float(rule["prediction_change_threshold"]),
            float(rule["coverage_ratio_threshold"]),
        )
        selected = run[run["support_budget"].eq(budget)].iloc[0]
        rows.append(
            {
                "split": split,
                "seed": int(seed),
                "heldout_corner": corner,
                "stop_budget": budget,
                "query_reduction_pct": 100.0 * (96 - budget) / 96,
                "delay_r2": float(selected["delay_r2"]),
                "full_delay_r2": float(run.loc[run["support_budget"].eq(96), "delay_r2"].iloc[0]),
                "delay_r2_gap_to_full": float(selected["delay_r2_gap_to_full"]),
                "gap_le_0p02": bool(selected["delay_r2_gap_to_full"] <= 0.02),
                "gap_le_0p05": bool(selected["delay_r2_gap_to_full"] <= 0.05),
                "worst_family_delay_r2": float(selected["worst_family_delay_r2"]),
                "worst_variant_delay_r2": float(selected["worst_variant_delay_r2"]),
            }
        )
    return pd.DataFrame(rows)


def summarize(rows: pd.DataFrame) -> dict[str, float | int]:
    return {
        "runs": len(rows),
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


def fixed_budget_rows(frame: pd.DataFrame, budget: int, split: str) -> pd.DataFrame:
    selected = frame[frame["support_budget"].eq(budget)].copy()
    selected["split"] = split
    selected["stop_budget"] = budget
    selected["query_reduction_pct"] = 100.0 * (96 - budget) / 96
    selected["gap_le_0p02"] = selected["delay_r2_gap_to_full"].le(0.02)
    selected["gap_le_0p05"] = selected["delay_r2_gap_to_full"].le(0.05)
    return selected.rename(columns={"worst_variant_delay_r2": "worst_variant_delay_r2"})


def main() -> int:
    frame = pd.read_csv(TRAJECTORY)
    development = frame[frame["seed"].isin(DEVELOPMENT_SEEDS)].copy()
    confirmation = frame[frame["seed"].isin(CONFIRMATION_SEEDS)].copy()
    candidates = []
    for minimum, preq, change, coverage in product(
        [16, 32, 48, 64],
        [0.15, 0.25, 0.40, 0.60, 1.00],
        [0.02, 0.05, 0.10, 0.20, 0.40],
        [0.35, 0.50, 0.65, 0.80],
    ):
        rule = {
            "minimum_budget": minimum,
            "prequential_nmae_threshold": preq,
            "prediction_change_threshold": change,
            "coverage_ratio_threshold": coverage,
        }
        rows = apply_rule(development, rule, "development")
        stats = summarize(rows)
        if stats["gap_le_0p02_rate"] >= 8 / 9 and stats["maximum_delay_r2_gap_to_full"] <= 0.05:
            candidates.append((stats["median_stop_budget"], stats["median_delay_r2_gap_to_full"], rule, stats))
    if candidates:
        candidates.sort(key=lambda item: (item[0], item[1]))
        _, _, locked_rule, development_stats = candidates[0]
        selection_status = "development_constraints_satisfied"
    else:
        locked_rule = {
            "minimum_budget": 64,
            "prequential_nmae_threshold": 1.00,
            "prediction_change_threshold": 0.40,
            "coverage_ratio_threshold": 0.80,
        }
        development_rows = apply_rule(development, locked_rule, "development")
        development_stats = summarize(development_rows)
        selection_status = "fallback_rule_no_candidate_met_development_constraints"

    development_rows = apply_rule(development, locked_rule, "development")
    confirmation_rows = apply_rule(confirmation, locked_rule, "confirmation")
    all_rows = pd.concat([development_rows, confirmation_rows], ignore_index=True)
    confirmation_stats = summarize(confirmation_rows)
    fixed48 = fixed_budget_rows(confirmation, 48, "confirmation_fixed_48")
    fixed64 = fixed_budget_rows(confirmation, 64, "confirmation_fixed_64")
    comparison = {
        "locked_rule": confirmation_stats,
        "fixed_48": summarize(fixed48),
        "fixed_64": summarize(fixed64),
    }

    OUTPUT.mkdir(parents=True, exist_ok=True)
    all_rows.to_csv(OUTPUT / "stopping_decisions.csv", index=False)
    pd.DataFrame(
        [
            {"method": "locked_rule", **confirmation_stats},
            {"method": "fixed_48", **summarize(fixed48)},
            {"method": "fixed_64", **summarize(fixed64)},
        ]
    ).to_csv(OUTPUT / "stopping_confirmation_summary.csv", index=False)
    protocol = {
        "selection_status": selection_status,
        "development_seeds": sorted(DEVELOPMENT_SEEDS),
        "confirmation_seeds": sorted(CONFIRMATION_SEEDS),
        "success_definition": "delay R2 gap to the measured 96-query reference <= 0.02",
        "rule_requires_two_consecutive_eligible_batches": True,
        "locked_rule": locked_rule,
        "development_summary": development_stats,
        "confirmation_comparison": comparison,
    }
    (OUTPUT / "stopping_protocol_and_results.json").write_text(json.dumps(protocol, indent=2), encoding="utf-8")
    report = [
        "# Validation-blind stopping rule",
        "",
        f"Selection status: `{selection_status}`.",
        "",
        f"Locked rule: `{json.dumps(locked_rule, sort_keys=True)}`.",
        "",
        "The rule uses only prequential delay error, model prediction change, and feature-space coverage. "
        "Seeds 0--2 were used for threshold development; seeds 3--4 were held back for confirmation.",
        "",
        "## Confirmation result",
        "",
        f"- Median stop budget: {confirmation_stats['median_stop_budget']:.0f}/96.",
        f"- Median query reduction: {confirmation_stats['median_query_reduction_pct']:.1f}%.",
        f"- Gap <= 0.02 success rate: {confirmation_stats['gap_le_0p02_rate']:.3f}.",
        f"- Median gap to full reference: {confirmation_stats['median_delay_r2_gap_to_full']:.4f}.",
        f"- Maximum gap to full reference: {confirmation_stats['maximum_delay_r2_gap_to_full']:.4f}.",
    ]
    (OUTPUT / "stopping_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps(protocol, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
