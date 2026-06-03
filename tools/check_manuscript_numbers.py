#!/usr/bin/env python3
"""Check that key manuscript numbers match the generated result files."""

from __future__ import annotations

import csv
import json
import statistics
import sys
from datetime import date
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEX_PATH = PROJECT_ROOT / "manuscript" / "microelectronics_journal_submission.tex"
REPORT_PATH = PROJECT_ROOT / "manuscript" / "manuscript_numeric_consistency_audit.md"


@dataclass
class Check:
    label: str
    expected: str
    source: str
    passed: bool


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def fmt(value: float, places: int = 4) -> str:
    return f"{value:.{places}f}"


def contains(tex: str, value: str) -> bool:
    return value in tex


def add(checks: list[Check], tex: str, label: str, value: str, source: str) -> None:
    checks.append(Check(label=label, expected=value, source=source, passed=contains(tex, value)))


def best_transfer_summary(rows: list[dict[str, str]], target: str, k: int) -> dict[str, float]:
    by_cell: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        if row["experiment"] != "cell_transfer" or row["target"] != target:
            continue
        if int(float(row["fewshot_k"])) != k:
            continue
        by_cell.setdefault(row["heldout_cell"], []).append(row)

    best = []
    for cell_rows in by_cell.values():
        best.append(max(cell_rows, key=lambda row: float(row["r2"])))
    return {
        "median_r2": statistics.median(float(row["r2"]) for row in best),
        "min_r2": min(float(row["r2"]) for row in best),
        "median_mae": statistics.median(float(row["mae"]) for row in best),
        "median_mape": statistics.median(float(row["mape_pct"]) for row in best),
    }


def best_scratch_median(rows: list[dict[str, str]], target: str, k: int) -> float:
    by_cell: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        if row["experiment"] != "cell_fewshot_from_scratch" or row["target"] != target:
            continue
        if int(float(row["fewshot_k"])) != k:
            continue
        by_cell.setdefault(row["heldout_cell"], []).append(row)
    best = [max(cell_rows, key=lambda row: float(row["r2"])) for cell_rows in by_cell.values()]
    return statistics.median(float(row["r2"]) for row in best)


def source_row(rows: list[dict[str, str]], target: str, model: str, protocol: str, hf_weight: str | None = None) -> dict[str, str]:
    for row in rows:
        if row["target"] != target or row["model"] != model or row["protocol"] != protocol:
            continue
        if hf_weight is None or row["hf_weight"] == hf_weight:
            return row
    raise KeyError((target, model, protocol, hf_weight))


def active_row(rows: list[dict[str, str]], target: str, labeled_rows: int) -> dict[str, str]:
    for row in rows:
        if row["target"] == target and int(row["labeled_rows"]) == labeled_rows:
            return row
    raise KeyError((target, labeled_rows))


def match_row(rows: list[dict[str, str]], **criteria: str) -> dict[str, str]:
    for row in rows:
        if all(row.get(key) == value for key, value in criteria.items()):
            return row
    raise KeyError(criteria)


def main() -> int:
    tex = TEX_PATH.read_text(encoding="utf-8")
    checks: list[Check] = []

    dataset_rows = read_csv(PROJECT_ROOT / "data" / "dataset_v2_spice_320.csv")
    add(checks, tex, "dataset row count", str(len(dataset_rows)), "data/dataset_v2_spice_320.csv")
    for cell in ["INV", "NAND2", "NOR2", "XOR2"]:
        count = sum(1 for row in dataset_rows if row["cell_type"] == cell)
        add(checks, tex, f"{cell} row count", str(count), "data/dataset_v2_spice_320.csv")

    v3_dataset_rows = read_csv(PROJECT_ROOT / "data" / "dataset_v3_spice_480.csv")
    add(checks, tex, "V3 dataset row count", str(len(v3_dataset_rows)), "data/dataset_v3_spice_480.csv")
    for cell in ["INV", "NAND2", "NOR2", "XOR2"]:
        count = sum(1 for row in v3_dataset_rows if row["cell_type"] == cell)
        add(checks, tex, f"V3 {cell} row count", str(count), "data/dataset_v3_spice_480.csv")
        for corner in ["ff", "ss", "typical"]:
            cell_corner_count = sum(
                1 for row in v3_dataset_rows if row["cell_type"] == cell and row["corner"] == corner
            )
            add(
                checks,
                tex,
                f"V3 {cell} {corner} row count",
                str(cell_corner_count),
                "data/dataset_v3_spice_480.csv",
            )
    for corner in ["ff", "ss", "typical"]:
        corner_count = sum(1 for row in v3_dataset_rows if row["corner"] == corner)
        add(checks, tex, f"V3 {corner} row count", str(corner_count), "data/dataset_v3_spice_480.csv")

    for col in ["Wn_um", "Wp_Wn_ratio", "Vdd", "Temp", "Cload_fF", "slew_ps"]:
        values = [float(row[col]) for row in dataset_rows]
        add(checks, tex, f"{col} minimum", fmt(min(values)), "data/dataset_v2_spice_320.csv")
        add(checks, tex, f"{col} maximum", fmt(max(values)), "data/dataset_v2_spice_320.csv")

    for cell in ["INV", "NAND2", "NOR2", "XOR2"]:
        rows = [row for row in dataset_rows if row["cell_type"] == cell]
        for col in ["delay_avg_ns", "power_avg_uW"]:
            values = [float(row[col]) for row in rows]
            add(checks, tex, f"{cell} {col} min", fmt(min(values)), "data/dataset_v2_spice_320.csv")
            add(checks, tex, f"{cell} {col} max", fmt(max(values)), "data/dataset_v2_spice_320.csv")
            add(checks, tex, f"{cell} {col} mean", fmt(statistics.mean(values)), "data/dataset_v2_spice_320.csv")

    model_summary = read_csv(PROJECT_ROOT / "results" / "v2_robustness" / "v2_model_zoo_repeated_summary.csv")
    model_specs = [
        ("delay_avg_ns", "GradientBoosting"),
        ("delay_avg_ns", "ExtraTrees"),
        ("power_avg_uW", "MLP"),
        ("power_avg_uW", "HistGradientBoosting"),
        ("power_avg_uW", "GradientBoosting"),
    ]
    for target, model in model_specs:
        row = match_row(model_summary, target=target, model=model)
        source = "results/v2_robustness/v2_model_zoo_repeated_summary.csv"
        add(checks, tex, f"{target} {model} repeated median R2", fmt(float(row["median_r2"])), source)
        add(checks, tex, f"{target} {model} repeated q25 R2", fmt(float(row["q25_r2"])), source)
        add(checks, tex, f"{target} {model} repeated q75 R2", fmt(float(row["q75_r2"])), source)
        add(checks, tex, f"{target} {model} repeated min R2", fmt(float(row["min_r2"])), source)
        add(checks, tex, f"{target} {model} repeated median MAE", fmt(float(row["median_mae"])), source)
        add(checks, tex, f"{target} {model} repeated median MAPE", fmt(float(row["median_mape_pct"])), source)

    feature_summary = read_csv(PROJECT_ROOT / "results" / "v2_robustness" / "v2_feature_ablation_summary.csv")
    feature_specs = [
        ("delay_avg_ns", "full"),
        ("delay_avg_ns", "no_cell_or_arc"),
        ("delay_avg_ns", "no_corner"),
        ("delay_avg_ns", "no_load_slew"),
        ("power_avg_uW", "full"),
        ("power_avg_uW", "no_cell_or_arc"),
        ("power_avg_uW", "no_load_slew"),
        ("power_avg_uW", "sizing_pvt_only"),
    ]
    for target, feature_set in feature_specs:
        row = match_row(feature_summary, target=target, feature_set=feature_set)
        source = "results/v2_robustness/v2_feature_ablation_summary.csv"
        add(checks, tex, f"{target} {feature_set} median R2", fmt(float(row["median_r2"])), source)
        add(checks, tex, f"{target} {feature_set} q25 R2", fmt(float(row["q25_r2"])), source)
        add(checks, tex, f"{target} {feature_set} q75 R2", fmt(float(row["q75_r2"])), source)
        add(checks, tex, f"{target} {feature_set} median MAE", fmt(float(row["median_mae"])), source)
        add(checks, tex, f"{target} {feature_set} median MAPE", fmt(float(row["median_mape_pct"])), source)

    learning_summary = read_csv(PROJECT_ROOT / "results" / "v2_robustness" / "v2_learning_curve_summary.csv")
    for train_rows in ["40", "120", "256"]:
        for target in ["delay_avg_ns", "power_avg_uW"]:
            row = match_row(learning_summary, target=target, train_rows=train_rows)
            add(
                checks,
                tex,
                f"{target} learning {train_rows} rows median R2",
                fmt(float(row["median_r2"])),
                "results/v2_robustness/v2_learning_curve_summary.csv",
            )

    corner_summary = read_csv(PROJECT_ROOT / "results" / "v2_robustness" / "v2_corner_holdout_summary.csv")
    for corner in ["ff", "ss", "typical"]:
        for target in ["delay_avg_ns", "power_avg_uW"]:
            row = match_row(corner_summary, target=target, feature_set="full", heldout_corner=corner)
            add(
                checks,
                tex,
                f"{target} corner {corner} holdout R2",
                fmt(float(row["median_r2"])),
                "results/v2_robustness/v2_corner_holdout_summary.csv",
            )

    transfer_summary = read_csv(PROJECT_ROOT / "results" / "v2_robustness" / "v2_transfer_robustness_summary.csv")
    transfer_specs = [
        ("delay_avg_ns", "source_plus_target_support", "0"),
        ("delay_avg_ns", "source_plus_target_support", "20"),
        ("delay_avg_ns", "source_plus_target_support", "40"),
        ("delay_avg_ns", "target_support_only", "20"),
        ("delay_avg_ns", "target_support_only", "40"),
        ("power_avg_uW", "source_plus_target_support", "0"),
        ("power_avg_uW", "source_plus_target_support", "20"),
        ("power_avg_uW", "source_plus_target_support", "40"),
        ("power_avg_uW", "target_support_only", "20"),
        ("power_avg_uW", "target_support_only", "40"),
    ]
    transfer_by_key: dict[tuple[str, str, str], dict[str, str]] = {}
    for target, protocol, k in transfer_specs:
        row = match_row(transfer_summary, target=target, training_protocol=protocol, fewshot_k=k)
        transfer_by_key[(target, protocol, k)] = row
        source = "results/v2_robustness/v2_transfer_robustness_summary.csv"
        add(checks, tex, f"{target} {protocol} k={k} median R2", fmt(float(row["median_r2"])), source)
        add(checks, tex, f"{target} {protocol} k={k} min R2", fmt(float(row["min_r2"])), source)
        add(checks, tex, f"{target} {protocol} k={k} median MAE", fmt(float(row["median_mae"])), source)
    delay_gain_40 = float(transfer_by_key[("delay_avg_ns", "source_plus_target_support", "40")]["median_r2"]) - float(transfer_by_key[("delay_avg_ns", "target_support_only", "40")]["median_r2"])
    power_gain_40 = float(transfer_by_key[("power_avg_uW", "source_plus_target_support", "40")]["median_r2"]) - float(transfer_by_key[("power_avg_uW", "target_support_only", "40")]["median_r2"])
    delay_gain_20 = float(transfer_by_key[("delay_avg_ns", "source_plus_target_support", "20")]["median_r2"]) - float(transfer_by_key[("delay_avg_ns", "target_support_only", "20")]["median_r2"])
    power_gain_20 = float(transfer_by_key[("power_avg_uW", "source_plus_target_support", "20")]["median_r2"]) - float(transfer_by_key[("power_avg_uW", "target_support_only", "20")]["median_r2"])
    add(checks, tex, "delay k=40 transfer improvement", fmt(delay_gain_40), "results/v2_robustness/v2_transfer_robustness_summary.csv")
    add(checks, tex, "power k=40 transfer improvement", fmt(power_gain_40), "results/v2_robustness/v2_transfer_robustness_summary.csv")
    add(checks, tex, "delay k=20 transfer improvement", fmt(delay_gain_20), "results/v2_robustness/v2_transfer_robustness_summary.csv")
    add(checks, tex, "power k=20 transfer improvement", fmt(power_gain_20), "results/v2_robustness/v2_transfer_robustness_summary.csv")

    source_rows = read_csv(PROJECT_ROOT / "results" / "source_aware" / "source_aware_ablation_summary.csv")
    source_specs = [
        ("delay_ns", "GradientBoosting", "hf_only", None),
        ("delay_ns", "GradientBoosting", "naive_merge_equal_weight", None),
        ("delay_ns", "GradientBoosting", "weighted_merge_no_source", "1.5"),
        ("delay_ns", "GradientBoosting", "lf_only", None),
        ("power_uW", "GradientBoosting", "hf_only", None),
        ("power_uW", "GradientBoosting", "weighted_merge_no_source", "1.5"),
    ]
    for target, model, protocol, weight in source_specs:
        row = source_row(source_rows, target, model, protocol, weight)
        add(checks, tex, f"{target} {protocol} {weight or ''} median R2", fmt(float(row["median_r2"])), "results/source_aware/source_aware_ablation_summary.csv")
        add(checks, tex, f"{target} {protocol} {weight or ''} median MAE", fmt(float(row["median_mae"])), "results/source_aware/source_aware_ablation_summary.csv")

    active_rows = read_csv(PROJECT_ROOT / "results" / "v2_active_learning" / "v2_active_learning_budget_comparison.csv")
    for target in ["delay_avg_ns", "power_avg_uW"]:
        for budget in [120, 200]:
            row = active_row(active_rows, target, budget)
            add(checks, tex, f"{target} active {budget} random R2", fmt(float(row["median_r2_random"])), "results/v2_active_learning/v2_active_learning_budget_comparison.csv")
            add(checks, tex, f"{target} active {budget} uncertainty R2", fmt(float(row["median_r2_uncertainty"])), "results/v2_active_learning/v2_active_learning_budget_comparison.csv")
            add(checks, tex, f"{target} active {budget} hybrid R2", fmt(float(row["median_r2_hybrid_random_then_uncertainty"])), "results/v2_active_learning/v2_active_learning_budget_comparison.csv")

    ranking_summary = read_csv(PROJECT_ROOT / "results" / "v2_robustness" / "v2_candidate_ranking_summary.csv")
    ranking_specs = [
        ("surrogate_top_score", "20"),
        ("random_selection", "10000"),
    ]
    for selection, runs in ranking_specs:
        row = match_row(ranking_summary, selection=selection)
        source = "results/v2_robustness/v2_candidate_ranking_summary.csv"
        add(checks, tex, f"{selection} runs", runs, source)
        for key in ["median_top10_hits", "median_top20_hits", "median_actual_rank"]:
            value = float(row[key])
            text = str(int(value)) if value.is_integer() else str(value)
            add(checks, tex, f"{selection} {key}", text, source)
    ranking_rows = read_csv(PROJECT_ROOT / "results" / "v2_robustness" / "v2_candidate_ranking_robustness.csv")
    heldout_rows = next(int(row["test_rows"]) for row in ranking_rows if row["selection"] == "surrogate_top_score")
    add(checks, tex, "candidate held-out rows", str(heldout_rows), "results/v2_robustness/v2_candidate_ranking_robustness.csv")

    v3_model_summary = read_csv(PROJECT_ROOT / "results" / "v3_robustness" / "v3_model_zoo_repeated_summary.csv")
    v3_model_specs = [
        ("delay_avg_ns", "SVR_RBF"),
        ("delay_avg_ns", "GradientBoosting"),
        ("power_avg_uW", "MLP"),
        ("power_avg_uW", "GradientBoosting"),
    ]
    for target, model in v3_model_specs:
        row = match_row(v3_model_summary, target=target, model=model)
        source = "results/v3_robustness/v3_model_zoo_repeated_summary.csv"
        add(checks, tex, f"V3 {target} {model} repeated median R2", fmt(float(row["median_r2"])), source)

    v3_external = read_csv(PROJECT_ROOT / "results" / "v3_scale_validation" / "v3_external_validation.csv")
    v3_external_specs = [
        ("delay_avg_ns", "GradientBoosting"),
        ("power_avg_uW", "GradientBoosting"),
        ("power_avg_uW", "MLP"),
    ]
    for target, model in v3_external_specs:
        row = match_row(v3_external, target=target, model=model)
        source = "results/v3_scale_validation/v3_external_validation.csv"
        add(checks, tex, f"V2-to-V3 {target} {model} R2", fmt(float(row["r2"])), source)
        add(checks, tex, f"V2-to-V3 {target} {model} MAE", fmt(float(row["mae"])), source)

    v3_candidate_summary = read_csv(
        PROJECT_ROOT / "results" / "v3_scale_validation" / "v3_external_candidate_ranking_summary.csv"
    )
    for selection in ["v2_surrogate_top_score", "random_selection"]:
        row = match_row(v3_candidate_summary, selection=selection)
        source = "results/v3_scale_validation/v3_external_candidate_ranking_summary.csv"
        for key in ["runs", "median_top10_hits", "median_top20_hits"]:
            value = float(row[key])
            text = str(int(value)) if value.is_integer() else str(value)
            add(checks, tex, f"V3 {selection} {key}", text, source)

    v3_corner_support = read_csv(PROJECT_ROOT / "results" / "v3_scale_validation" / "v3_corner_support_summary.csv")
    for support_rows in ["0", "12", "24", "48"]:
        for target in ["delay_avg_ns", "power_avg_uW"]:
            row = match_row(
                v3_corner_support,
                target=target,
                heldout_corner="ff",
                support_rows=support_rows,
            )
            add(
                checks,
                tex,
                f"V3 ff support {support_rows} {target} median R2",
                fmt(float(row["median_r2"])),
                "results/v3_scale_validation/v3_corner_support_summary.csv",
            )

    failed = [check for check in checks if not check.passed]
    lines = [
        "# Manuscript Numeric Consistency Audit",
        "",
        f"Updated: {date.today().isoformat()}",
        "",
        "This report is generated by `tools/check_manuscript_numbers.py`. It verifies that key numeric claims in `manuscript/microelectronics_journal_submission.tex` are present and match the project data/result files.",
        "",
        f"- Checks run: {len(checks)}",
        f"- Passed: {len(checks) - len(failed)}",
        f"- Failed: {len(failed)}",
        "",
        "| Status | Claim | Expected text | Source |",
        "|---|---|---:|---|",
    ]
    for check in checks:
        status = "PASS" if check.passed else "FAIL"
        lines.append(f"| {status} | {check.label} | `{check.expected}` | `{check.source}` |")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    for check in checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"[{status}] {check.label}: expected {check.expected} from {check.source}")
    print(f"Summary: {len(failed)} failure(s), {len(checks)} check(s)")
    print(f"Wrote {REPORT_PATH.relative_to(PROJECT_ROOT)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
