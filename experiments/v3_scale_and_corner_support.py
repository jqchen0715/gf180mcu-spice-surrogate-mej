#!/usr/bin/env python3
"""Scale-up and corner-support validation for the expanded SPICE dataset.

This script addresses two reviewer-facing risks that are not resolved by a
random split alone:

1. whether a model trained on the original 320-row V2 dataset transfers to an
   independently generated 480-row SPICE validation dataset; and
2. whether the weak leave-one-corner delay extrapolation can be converted into
   a calibration problem by adding a small number of same-corner SPICE support
   samples.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import warnings

import numpy as np
import pandas as pd

from v2_robustness_ablation import (
    FEATURE_SETS,
    TARGETS,
    build_pipeline,
    load_dataset,
    markdown_table,
    metrics,
    model_specs,
    normalized_score,
    summarize_repeated,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRAIN_DATASET = PROJECT_ROOT / "data" / "dataset_v2_spice_320.csv"
DEFAULT_VALIDATION_DATASET = PROJECT_ROOT / "data" / "dataset_v3_spice_480.csv"
DEFAULT_OUTDIR = PROJECT_ROOT / "results" / "v3_scale_validation"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run V3 scale-up and corner-support validation.")
    parser.add_argument("--train-dataset", type=Path, default=DEFAULT_TRAIN_DATASET)
    parser.add_argument("--validation-dataset", type=Path, default=DEFAULT_VALIDATION_DATASET)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--seeds", nargs="*", type=int, default=list(range(20)))
    parser.add_argument("--support-rows", nargs="*", type=int, default=[0, 12, 24, 48])
    parser.add_argument("--top-n", type=int, default=24)
    parser.add_argument("--random-ranking-trials", type=int, default=10000)
    return parser.parse_args()


def fit_external_model(
    train: pd.DataFrame,
    test: pd.DataFrame,
    target: str,
    model_name: str,
    seed: int = 0,
) -> np.ndarray:
    numeric, categorical = FEATURE_SETS["full"]
    features = numeric + categorical
    pipe = build_pipeline(model_specs(seed)[model_name], numeric, categorical)
    pipe.fit(train[features], train[target])
    return pipe.predict(test[features])


def run_external_validation(train: pd.DataFrame, validation: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for target in TARGETS:
        for model_name in ["GradientBoosting", "SVR_RBF", "MLP"]:
            pred = fit_external_model(train, validation, target, model_name, seed=0)
            row: dict[str, object] = {
                "experiment": "v2_train_v3_external_validation",
                "target": target,
                "model": model_name,
                "train_rows": len(train),
                "test_rows": len(validation),
            }
            row.update(metrics(validation[target].to_numpy(), pred))
            rows.append(row)
    return pd.DataFrame(rows)


def ranking_row(
    pred: pd.DataFrame,
    selected_indices: np.ndarray,
    selection: str,
    top_n: int,
) -> dict[str, object]:
    top10_cut = max(1, int(np.ceil(len(pred) * 0.10)))
    top20_cut = max(1, int(np.ceil(len(pred) * 0.20)))
    selected = pred.iloc[selected_indices]
    return {
        "experiment": "v2_train_v3_candidate_validation",
        "selection": selection,
        "test_rows": len(pred),
        "selected_candidates": top_n,
        "top10_hits": int((selected["actual_rank"] <= top10_cut).sum()),
        "top20_hits": int((selected["actual_rank"] <= top20_cut).sum()),
        "median_actual_rank": float(selected["actual_rank"].median()),
        "mean_actual_score": float(selected["actual_score"].mean()),
        "spearman_pred_actual_score": float(pred["pred_score"].corr(pred["actual_score"], method="spearman")),
    }


def run_external_candidate_validation(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    top_n: int,
    random_trials: int,
) -> pd.DataFrame:
    pred = validation.copy().reset_index(drop=True)
    for target in TARGETS:
        pred_values = fit_external_model(train, validation, target, "GradientBoosting", seed=0)
        pred[f"pred_{target}"] = pred_values

    pred["pred_score"] = normalized_score(pred, "pred_delay_avg_ns", "pred_power_avg_uW")
    pred["actual_score"] = normalized_score(pred, "delay_avg_ns", "power_avg_uW")
    pred["actual_rank"] = pred["actual_score"].rank(method="min", ascending=True)

    rows: list[dict[str, object]] = []
    selected_indices = pred.sort_values("pred_score").head(top_n).index.to_numpy()
    rows.append(ranking_row(pred, selected_indices, "v2_surrogate_top_score", top_n))

    rng = np.random.default_rng(20260602)
    for trial in range(random_trials):
        random_indices = rng.choice(pred.index.to_numpy(), size=top_n, replace=False)
        row = ranking_row(pred, random_indices, "random_selection", top_n)
        row["trial"] = trial
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_external_candidate(results: pd.DataFrame) -> pd.DataFrame:
    summary = (
        results.groupby("selection")
        .agg(
            runs=("top10_hits", "count"),
            median_top10_hits=("top10_hits", "median"),
            median_top20_hits=("top20_hits", "median"),
            median_actual_rank=("median_actual_rank", "median"),
            median_actual_score=("mean_actual_score", "median"),
            median_spearman=("spearman_pred_actual_score", "median"),
        )
        .reset_index()
    )
    random = results[results["selection"] == "random_selection"]
    surrogate = results[results["selection"] == "v2_surrogate_top_score"]
    if not random.empty and not surrogate.empty:
        surrogate_row = surrogate.iloc[0]
        mask = summary["selection"] == "v2_surrogate_top_score"
        summary["empirical_p_top10_ge_surrogate"] = ""
        summary["empirical_p_top20_ge_surrogate"] = ""
        summary["empirical_p_rank_le_surrogate"] = ""
        summary.loc[mask, "empirical_p_top10_ge_surrogate"] = float(
            (random["top10_hits"] >= surrogate_row["top10_hits"]).mean()
        )
        summary.loc[mask, "empirical_p_top20_ge_surrogate"] = float(
            (random["top20_hits"] >= surrogate_row["top20_hits"]).mean()
        )
        summary.loc[mask, "empirical_p_rank_le_surrogate"] = float(
            (random["median_actual_rank"] <= surrogate_row["median_actual_rank"]).mean()
        )
    return summary


def sample_corner_support(corner_df: pd.DataFrame, support_rows: int, seed: int) -> pd.DataFrame:
    if support_rows <= 0:
        return corner_df.iloc[0:0].copy()

    cells = sorted(corner_df["cell_type"].unique())
    base = support_rows // len(cells)
    remainder = support_rows % len(cells)
    support_parts: list[pd.DataFrame] = []
    for idx, cell in enumerate(cells):
        cell_df = corner_df[corner_df["cell_type"] == cell]
        n = base + (1 if idx < remainder else 0)
        n = min(n, max(len(cell_df) - 1, 0))
        if n > 0:
            support_parts.append(cell_df.sample(n=n, random_state=seed + idx))
    if not support_parts:
        return corner_df.iloc[0:0].copy()
    return pd.concat(support_parts).sort_index()


def run_corner_support(validation: pd.DataFrame, seeds: list[int], support_rows_list: list[int]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for heldout_corner in sorted(validation["corner"].unique()):
        train_base = validation[validation["corner"] != heldout_corner].copy()
        corner_df = validation[validation["corner"] == heldout_corner].copy()
        for seed in seeds:
            for support_rows in support_rows_list:
                support = sample_corner_support(corner_df, support_rows, seed + support_rows)
                query = corner_df.drop(index=support.index)
                train = pd.concat([train_base, support], ignore_index=True)
                for target in TARGETS:
                    pred = fit_external_model(train, query, target, "GradientBoosting", seed=seed)
                    row: dict[str, object] = {
                        "experiment": "corner_support_calibration",
                        "target": target,
                        "model": "GradientBoosting",
                        "heldout_corner": heldout_corner,
                        "support_rows": len(support),
                        "train_rows": len(train),
                        "test_rows": len(query),
                        "seed": seed,
                    }
                    row.update(metrics(query[target].to_numpy(), pred))
                    rows.append(row)
    return pd.DataFrame(rows)


def write_report(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    external: pd.DataFrame,
    ranking_summary: pd.DataFrame,
    corner_summary: pd.DataFrame,
    outdir: Path,
) -> None:
    corner_compact = corner_summary.sort_values(["target", "heldout_corner", "support_rows"])
    lines = [
        "# V3 Scale-Up and Corner-Support Validation",
        "",
        "## Dataset",
        "",
        f"- V2 training rows: {len(train)} publication-eligible GF180MCU/ngspice rows.",
        f"- V3 validation rows: {len(validation)} publication-eligible GF180MCU/ngspice rows.",
        f"- V3 cells: {', '.join(sorted(validation['cell_type'].unique()))}.",
        f"- V3 corners: {', '.join(sorted(validation['corner'].unique()))}.",
        "",
        "## V2-Trained External Validation on V3",
        "",
        markdown_table(external),
        "",
        "## V2-Trained Candidate Ranking on V3",
        "",
        markdown_table(ranking_summary),
        "",
        "## Corner-Support Calibration on V3",
        "",
        markdown_table(
            corner_compact[
                [
                    "target",
                    "heldout_corner",
                    "support_rows",
                    "runs",
                    "median_r2",
                    "q25_r2",
                    "q75_r2",
                    "median_mae",
                    "median_mape_pct",
                ]
            ]
        ),
    ]
    (outdir / "v3_scale_validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (outdir / "v3_scale_validation_summary.json").write_text(
        json.dumps(
            {
                "v2_train_rows": int(len(train)),
                "v3_validation_rows": int(len(validation)),
                "external_validation": external.to_dict(orient="records"),
                "candidate_ranking": ranking_summary.to_dict(orient="records"),
                "corner_support": corner_summary.to_dict(orient="records"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    args.outdir.mkdir(parents=True, exist_ok=True)

    train = load_dataset(args.train_dataset)
    validation = load_dataset(args.validation_dataset)
    external = run_external_validation(train, validation)
    ranking = run_external_candidate_validation(train, validation, args.top_n, args.random_ranking_trials)
    ranking_summary = summarize_external_candidate(ranking)
    corner_support = run_corner_support(validation, args.seeds, args.support_rows)
    corner_summary = summarize_repeated(corner_support, ["target", "heldout_corner", "support_rows"])

    external.to_csv(args.outdir / "v3_external_validation.csv", index=False)
    ranking.to_csv(args.outdir / "v3_external_candidate_ranking.csv", index=False)
    ranking_summary.to_csv(args.outdir / "v3_external_candidate_ranking_summary.csv", index=False)
    corner_support.to_csv(args.outdir / "v3_corner_support.csv", index=False)
    corner_summary.to_csv(args.outdir / "v3_corner_support_summary.csv", index=False)
    write_report(train, validation, external, ranking_summary, corner_summary, args.outdir)

    print(f"V2 train rows: {len(train)}")
    print(f"V3 validation rows: {len(validation)}")
    print(f"Wrote {args.outdir / 'v3_scale_validation_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
