#!/usr/bin/env python3
"""Robustness, ablation, and ranking checks for the V2 GF180MCU dataset.

The main V2 experiments establish the workflow. This script adds reviewer-facing
checks that are useful for a journal submission: repeated random splits, feature
group ablations, learning curves, leave-one-corner stress tests, repeated
leave-one-cell-out transfer, and candidate-ranking enrichment against a
random-selection baseline.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import warnings

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    ExtraTreesRegressor,
    GradientBoostingRegressor,
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVR


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = PROJECT_ROOT / "data" / "dataset_v2_spice_320.csv"
DEFAULT_OUTDIR = PROJECT_ROOT / "results" / "v2_robustness"

NUMERIC_FEATURES = [
    "Wn_um",
    "L_um",
    "Wp_Wn_ratio",
    "Vdd",
    "Temp",
    "Cload_fF",
    "slew_ps",
]
CATEGORICAL_FEATURES = ["cell_type", "input_arc", "corner"]
TARGETS = ["delay_avg_ns", "power_avg_uW"]

FEATURE_SETS = {
    "full": (NUMERIC_FEATURES, CATEGORICAL_FEATURES),
    "no_load_slew": (
        ["Wn_um", "L_um", "Wp_Wn_ratio", "Vdd", "Temp"],
        CATEGORICAL_FEATURES,
    ),
    "sizing_pvt_only": (
        ["Wn_um", "L_um", "Wp_Wn_ratio", "Vdd", "Temp"],
        [],
    ),
    "no_cell_or_arc": (NUMERIC_FEATURES, ["corner"]),
    "no_corner": (NUMERIC_FEATURES, ["cell_type", "input_arc"]),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run V2 robustness and ablation experiments.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--seeds", nargs="*", type=int, default=list(range(20)))
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--transfer-k", nargs="*", type=int, default=[0, 20, 40])
    parser.add_argument("--learning-curve-rows", nargs="*", type=int, default=[40, 80, 120, 160, 220, 256])
    parser.add_argument("--top-n", type=int, default=12)
    parser.add_argument("--random-ranking-trials", type=int, default=500)
    parser.add_argument("--output-prefix", default="v2", help="Prefix used for output filenames.")
    return parser.parse_args()


def one_hot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def preprocessor(numeric: list[str], categorical: list[str]) -> ColumnTransformer:
    transformers = []
    if numeric:
        transformers.append(("num", StandardScaler(), numeric))
    if categorical:
        transformers.append(("cat", one_hot_encoder(), categorical))
    return ColumnTransformer(transformers=transformers)


def model_specs(seed: int) -> dict[str, object]:
    return {
        "Ridge": Ridge(alpha=1.0),
        "SVR_RBF": SVR(kernel="rbf", C=10.0, epsilon=0.01),
        "RandomForest": RandomForestRegressor(
            n_estimators=300,
            min_samples_leaf=2,
            random_state=seed,
            n_jobs=-1,
        ),
        "ExtraTrees": ExtraTreesRegressor(
            n_estimators=300,
            min_samples_leaf=2,
            random_state=seed,
            n_jobs=-1,
        ),
        "GradientBoosting": GradientBoostingRegressor(random_state=seed),
        "HistGradientBoosting": HistGradientBoostingRegressor(
            max_iter=250,
            l2_regularization=1e-4,
            random_state=seed,
        ),
        "MLP": MLPRegressor(
            hidden_layer_sizes=(96, 48),
            activation="relu",
            alpha=1e-4,
            learning_rate_init=1e-3,
            max_iter=1500,
            early_stopping=True,
            validation_fraction=0.15,
            random_state=seed,
        ),
    }


def build_pipeline(model: object, numeric: list[str], categorical: list[str]) -> Pipeline:
    return Pipeline([("pre", preprocessor(numeric, categorical)), ("model", model)])


def load_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = set(NUMERIC_FEATURES + CATEGORICAL_FEATURES + TARGETS + ["status", "fidelity"])
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}")
    df = df[(df["status"] == "ok") & (df["fidelity"] == "SPICE_GF180MCU")].copy()
    if df.empty:
        raise ValueError("No publication-eligible SPICE_GF180MCU rows found.")
    return df.reset_index(drop=True)


def metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2 = float(r2_score(y_true, y_pred))
    denom = np.maximum(np.abs(y_true), 1e-12)
    mape = float(np.mean(np.abs((y_true - y_pred) / denom)) * 100)
    return {"r2": r2, "mae": mae, "rmse": rmse, "mape_pct": mape}


def fit_predict(
    train: pd.DataFrame,
    test: pd.DataFrame,
    target: str,
    model_name: str,
    seed: int,
    feature_set: str = "full",
) -> np.ndarray:
    numeric, categorical = FEATURE_SETS[feature_set]
    pipe = build_pipeline(model_specs(seed)[model_name], numeric, categorical)
    features = numeric + categorical
    pipe.fit(train[features], train[target])
    return pipe.predict(test[features])


def run_repeated_model_zoo(df: pd.DataFrame, seeds: list[int], test_size: float) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for seed in seeds:
        train, test = train_test_split(
            df,
            test_size=test_size,
            random_state=seed,
            stratify=df["cell_type"],
        )
        for target in TARGETS:
            for model_name in model_specs(seed):
                pred = fit_predict(train, test, target, model_name, seed, feature_set="full")
                row: dict[str, object] = {
                    "experiment": "repeated_random_split",
                    "seed": seed,
                    "target": target,
                    "model": model_name,
                    "feature_set": "full",
                    "train_rows": len(train),
                    "test_rows": len(test),
                }
                row.update(metrics(test[target].to_numpy(), pred))
                rows.append(row)
    return pd.DataFrame(rows)


def run_feature_ablation(df: pd.DataFrame, seeds: list[int], test_size: float) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for seed in seeds:
        train, test = train_test_split(
            df,
            test_size=test_size,
            random_state=seed,
            stratify=df["cell_type"],
        )
        for target in TARGETS:
            for feature_set in FEATURE_SETS:
                pred = fit_predict(train, test, target, "GradientBoosting", seed, feature_set)
                row: dict[str, object] = {
                    "experiment": "feature_ablation",
                    "seed": seed,
                    "target": target,
                    "model": "GradientBoosting",
                    "feature_set": feature_set,
                    "train_rows": len(train),
                    "test_rows": len(test),
                }
                row.update(metrics(test[target].to_numpy(), pred))
                rows.append(row)
    return pd.DataFrame(rows)


def stratified_subsample(train: pd.DataFrame, n_rows: int, seed: int) -> pd.DataFrame:
    if n_rows >= len(train):
        return train.copy()
    if n_rows < train["cell_type"].nunique():
        raise ValueError("Learning-curve sample size must be at least the number of cell types.")
    sampled, _ = train_test_split(
        train,
        train_size=n_rows,
        random_state=seed,
        stratify=train["cell_type"],
    )
    return sampled.copy()


def run_learning_curve(
    df: pd.DataFrame,
    seeds: list[int],
    test_size: float,
    train_sizes: list[int],
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for seed in seeds:
        train, test = train_test_split(
            df,
            test_size=test_size,
            random_state=seed,
            stratify=df["cell_type"],
        )
        usable_sizes = [size for size in train_sizes if size <= len(train)]
        if len(train) not in usable_sizes:
            usable_sizes.append(len(train))
        for train_size in sorted(set(usable_sizes)):
            subset = stratified_subsample(train, train_size, seed + train_size)
            for target in TARGETS:
                pred = fit_predict(subset, test, target, "GradientBoosting", seed, feature_set="full")
                row: dict[str, object] = {
                    "experiment": "learning_curve",
                    "seed": seed,
                    "target": target,
                    "model": "GradientBoosting",
                    "feature_set": "full",
                    "train_rows": len(subset),
                    "test_rows": len(test),
                }
                row.update(metrics(test[target].to_numpy(), pred))
                rows.append(row)
    return pd.DataFrame(rows)


def run_corner_holdout(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for heldout_corner in sorted(df["corner"].unique()):
        train = df[df["corner"] != heldout_corner].copy()
        test = df[df["corner"] == heldout_corner].copy()
        for target in TARGETS:
            for feature_set in ["full", "no_corner"]:
                pred = fit_predict(train, test, target, "GradientBoosting", 0, feature_set=feature_set)
                row: dict[str, object] = {
                    "experiment": "leave_one_corner_out",
                    "target": target,
                    "model": "GradientBoosting",
                    "feature_set": feature_set,
                    "heldout_corner": heldout_corner,
                    "train_rows": len(train),
                    "test_rows": len(test),
                }
                row.update(metrics(test[target].to_numpy(), pred))
                rows.append(row)
    return pd.DataFrame(rows)


def sample_target_cell(df: pd.DataFrame, cell: str, k: int, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    target_df = df[df["cell_type"] == cell]
    if k <= 0:
        return target_df.iloc[0:0].copy(), target_df.copy()
    support = target_df.sample(n=min(k, len(target_df) - 1), random_state=seed)
    query = target_df.drop(index=support.index)
    return support, query


def run_transfer_robustness(df: pd.DataFrame, seeds: list[int], transfer_k: list[int]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    cells = sorted(df["cell_type"].unique())
    for seed in seeds:
        for heldout_cell in cells:
            source = df[df["cell_type"] != heldout_cell]
            for k in transfer_k:
                support, query = sample_target_cell(df, heldout_cell, k, seed + k)
                transfer_train = pd.concat([source, support], ignore_index=True)
                for target in TARGETS:
                    pred = fit_predict(
                        transfer_train,
                        query,
                        target,
                        "GradientBoosting",
                        seed,
                        feature_set="full",
                    )
                    row: dict[str, object] = {
                        "experiment": "leave_one_cell_transfer",
                        "training_protocol": "source_plus_target_support",
                        "seed": seed,
                        "target": target,
                        "heldout_cell": heldout_cell,
                        "fewshot_k": k,
                        "model": "GradientBoosting",
                        "train_rows": len(transfer_train),
                        "test_rows": len(query),
                    }
                    row.update(metrics(query[target].to_numpy(), pred))
                    rows.append(row)

                    if k > 0:
                        scratch_pred = fit_predict(
                            support,
                            query,
                            target,
                            "GradientBoosting",
                            seed,
                            feature_set="full",
                        )
                        scratch_row: dict[str, object] = {
                            "experiment": "leave_one_cell_transfer",
                            "training_protocol": "target_support_only",
                            "seed": seed,
                            "target": target,
                            "heldout_cell": heldout_cell,
                            "fewshot_k": k,
                            "model": "GradientBoosting",
                            "train_rows": len(support),
                            "test_rows": len(query),
                        }
                        scratch_row.update(metrics(query[target].to_numpy(), scratch_pred))
                        rows.append(scratch_row)
    return pd.DataFrame(rows)


def normalized_score(df: pd.DataFrame, delay_col: str, power_col: str) -> pd.Series:
    delay_range = max(df[delay_col].max() - df[delay_col].min(), 1e-12)
    power_range = max(df[power_col].max() - df[power_col].min(), 1e-12)
    delay_norm = (df[delay_col] - df[delay_col].min()) / delay_range
    power_norm = (df[power_col] - df[power_col].min()) / power_range
    return 0.5 * delay_norm + 0.5 * power_norm


def ranking_row(
    pred: pd.DataFrame,
    selected_indices: np.ndarray,
    seed: int,
    selection: str,
    top_n: int,
) -> dict[str, object]:
    top10_cut = max(1, int(np.ceil(len(pred) * 0.10)))
    top20_cut = max(1, int(np.ceil(len(pred) * 0.20)))
    selected = pred.iloc[selected_indices]
    return {
        "experiment": "candidate_ranking",
        "seed": seed,
        "selection": selection,
        "test_rows": len(pred),
        "selected_candidates": top_n,
        "top10_hits": int((selected["actual_rank"] <= top10_cut).sum()),
        "top20_hits": int((selected["actual_rank"] <= top20_cut).sum()),
        "median_actual_rank": float(selected["actual_rank"].median()),
        "mean_actual_score": float(selected["actual_score"].mean()),
        "spearman_pred_actual_score": float(
            pred["pred_score"].corr(pred["actual_score"], method="spearman")
        ),
    }


def run_candidate_ranking(
    df: pd.DataFrame,
    seeds: list[int],
    test_size: float,
    top_n: int,
    random_trials: int,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for seed in seeds:
        train, test = train_test_split(
            df,
            test_size=test_size,
            random_state=seed,
            stratify=df["cell_type"],
        )
        pred = test.copy().reset_index(drop=True)
        for target in TARGETS:
            pred_values = fit_predict(train, test, target, "GradientBoosting", seed, feature_set="full")
            pred[f"pred_{target}"] = pred_values
        pred["pred_score"] = normalized_score(pred, "pred_delay_avg_ns", "pred_power_avg_uW")
        pred["actual_score"] = normalized_score(pred, "delay_avg_ns", "power_avg_uW")
        pred["actual_rank"] = pred["actual_score"].rank(method="min", ascending=True)

        selected_indices = pred.sort_values("pred_score").head(top_n).index.to_numpy()
        rows.append(ranking_row(pred, selected_indices, seed, "surrogate_top_score", top_n))

        rng = np.random.default_rng(seed + 5000)
        for trial in range(random_trials):
            random_indices = rng.choice(pred.index.to_numpy(), size=top_n, replace=False)
            random_row = ranking_row(pred, random_indices, seed, "random_selection", top_n)
            random_row["trial"] = trial
            rows.append(random_row)
    return pd.DataFrame(rows)


def summarize_repeated(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    return (
        df.groupby(group_cols)
        .agg(
            runs=("r2", "count"),
            median_r2=("r2", "median"),
            q25_r2=("r2", lambda s: float(s.quantile(0.25))),
            q75_r2=("r2", lambda s: float(s.quantile(0.75))),
            min_r2=("r2", "min"),
            median_mae=("mae", "median"),
            median_rmse=("rmse", "median"),
            median_mape_pct=("mape_pct", "median"),
        )
        .reset_index()
    )


def summarize_candidate_ranking(results: pd.DataFrame) -> pd.DataFrame:
    grouped = results.groupby(["selection"])
    summary = (
        grouped.agg(
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
    surrogate = results[results["selection"] == "surrogate_top_score"]
    if not random.empty and not surrogate.empty:
        surrogate_top10 = float(surrogate["top10_hits"].median())
        surrogate_top20 = float(surrogate["top20_hits"].median())
        surrogate_rank = float(surrogate["median_actual_rank"].median())
        top10_p = float((random["top10_hits"] >= surrogate_top10).mean())
        top20_p = float((random["top20_hits"] >= surrogate_top20).mean())
        rank_p = float((random["median_actual_rank"] <= surrogate_rank).mean())
        summary["empirical_p_top10_ge_surrogate"] = ""
        summary["empirical_p_top20_ge_surrogate"] = ""
        summary["empirical_p_rank_le_surrogate"] = ""
        mask = summary["selection"] == "surrogate_top_score"
        summary.loc[mask, "empirical_p_top10_ge_surrogate"] = top10_p
        summary.loc[mask, "empirical_p_top20_ge_surrogate"] = top20_p
        summary.loc[mask, "empirical_p_rank_le_surrogate"] = rank_p
    return summary


def markdown_table(df: pd.DataFrame) -> str:
    rendered = df.copy()
    for col in rendered.columns:
        if pd.api.types.is_numeric_dtype(rendered[col]):
            rendered[col] = rendered[col].map(lambda x: f"{x:.4f}")
        else:
            rendered[col] = rendered[col].astype(str)
    header = "| " + " | ".join(rendered.columns) + " |"
    sep = "| " + " | ".join(["---"] * len(rendered.columns)) + " |"
    rows = ["| " + " | ".join(row) + " |" for row in rendered.astype(str).to_numpy()]
    return "\n".join([header, sep] + rows)


def write_report(
    df: pd.DataFrame,
    model_zoo: pd.DataFrame,
    feature_ablation: pd.DataFrame,
    learning_curve: pd.DataFrame,
    corner_holdout: pd.DataFrame,
    transfer: pd.DataFrame,
    ranking: pd.DataFrame,
    outdir: Path,
    output_prefix: str,
) -> None:
    model_summary = summarize_repeated(model_zoo, ["target", "model"])
    feature_summary = summarize_repeated(feature_ablation, ["target", "feature_set"])
    learning_summary = summarize_repeated(learning_curve, ["target", "train_rows"])
    corner_summary = summarize_repeated(corner_holdout, ["target", "feature_set", "heldout_corner"])
    transfer_summary = summarize_repeated(
        transfer,
        ["target", "training_protocol", "fewshot_k"],
    )
    ranking_summary = summarize_candidate_ranking(ranking)
    dataset_label = output_prefix.upper()

    model_summary.to_csv(outdir / f"{output_prefix}_model_zoo_repeated_summary.csv", index=False)
    feature_summary.to_csv(outdir / f"{output_prefix}_feature_ablation_summary.csv", index=False)
    learning_summary.to_csv(outdir / f"{output_prefix}_learning_curve_summary.csv", index=False)
    corner_summary.to_csv(outdir / f"{output_prefix}_corner_holdout_summary.csv", index=False)
    transfer_summary.to_csv(outdir / f"{output_prefix}_transfer_robustness_summary.csv", index=False)
    ranking_summary.to_csv(outdir / f"{output_prefix}_candidate_ranking_summary.csv", index=False)

    best_models = (
        model_summary.sort_values(["target", "median_r2"], ascending=[True, False])
        .groupby("target")
        .head(4)
        .reset_index(drop=True)
    )
    feature_compact = feature_summary.sort_values(["target", "median_r2"], ascending=[True, False])
    learning_compact = learning_summary.sort_values(["target", "train_rows"])
    corner_compact = corner_summary.sort_values(["target", "feature_set", "heldout_corner"])
    transfer_compact = transfer_summary.sort_values(
        ["target", "training_protocol", "fewshot_k"],
        ascending=[True, True, True],
    )

    lines = [
        f"# {dataset_label} Robustness and Ablation Report",
        "",
        "## Dataset",
        "",
        f"- Rows used: {len(df)} publication-eligible GF180MCU/ngspice rows.",
        f"- Cells: {', '.join(sorted(df['cell_type'].unique()))}.",
        "- Targets: `delay_avg_ns` and `power_avg_uW`.",
        f"- All experiments use only the {dataset_label} SPICE dataset; no legacy data are used.",
        "",
        "## Repeated Random-Split Model Zoo",
        "",
        "Top four models per target by median R2 across repeated stratified splits:",
        "",
        markdown_table(
            best_models[
                [
                    "target",
                    "model",
                    "runs",
                    "median_r2",
                    "q25_r2",
                    "q75_r2",
                    "min_r2",
                    "median_mae",
                    "median_mape_pct",
                ]
            ]
        ),
        "",
        "## Gradient-Boosting Feature Ablation",
        "",
        markdown_table(
            feature_compact[
                [
                    "target",
                    "feature_set",
                    "runs",
                    "median_r2",
                    "q25_r2",
                    "q75_r2",
                    "median_mae",
                    "median_mape_pct",
                ]
            ]
        ),
        "",
        "## Gradient-Boosting Learning Curve",
        "",
        markdown_table(
            learning_compact[
                [
                    "target",
                    "train_rows",
                    "runs",
                    "median_r2",
                    "q25_r2",
                    "q75_r2",
                    "median_mae",
                    "median_mape_pct",
                ]
            ]
        ),
        "",
        "## Leave-One-Corner-Out Stress Test",
        "",
        markdown_table(
            corner_compact[
                [
                    "target",
                    "feature_set",
                    "heldout_corner",
                    "runs",
                    "median_r2",
                    "median_mae",
                    "median_mape_pct",
                ]
            ]
        ),
        "",
        "## Repeated Leave-One-Cell-Out Transfer",
        "",
        markdown_table(
            transfer_compact[
                [
                    "target",
                    "training_protocol",
                    "fewshot_k",
                    "runs",
                    "median_r2",
                    "min_r2",
                    "median_mae",
                    "median_mape_pct",
                ]
            ]
        ),
        "",
        "## Candidate-Ranking Enrichment",
        "",
        markdown_table(ranking_summary),
        "",
        "## Output Files",
        "",
        f"- `{output_prefix}_model_zoo_repeated.csv` and summary",
        f"- `{output_prefix}_feature_ablation.csv` and summary",
        f"- `{output_prefix}_learning_curve.csv` and summary",
        f"- `{output_prefix}_corner_holdout.csv` and summary",
        f"- `{output_prefix}_transfer_robustness.csv` and summary",
        f"- `{output_prefix}_candidate_ranking_robustness.csv` and summary",
    ]
    (outdir / f"{output_prefix}_robustness_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (outdir / f"{output_prefix}_robustness_summary.json").write_text(
        json.dumps(
            {
                "rows_used": int(len(df)),
                "cells": sorted(df["cell_type"].unique().tolist()),
                "targets": TARGETS,
                "best_models": best_models.to_dict(orient="records"),
                "feature_ablation": feature_summary.to_dict(orient="records"),
                "learning_curve": learning_summary.to_dict(orient="records"),
                "corner_holdout": corner_summary.to_dict(orient="records"),
                "transfer_robustness": transfer_summary.to_dict(orient="records"),
                "candidate_ranking": ranking_summary.to_dict(orient="records"),
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

    df = load_dataset(args.dataset)
    model_zoo = run_repeated_model_zoo(df, args.seeds, args.test_size)
    feature_ablation = run_feature_ablation(df, args.seeds, args.test_size)
    learning_curve = run_learning_curve(df, args.seeds, args.test_size, args.learning_curve_rows)
    corner_holdout = run_corner_holdout(df)
    transfer = run_transfer_robustness(df, args.seeds, args.transfer_k)
    ranking = run_candidate_ranking(
        df,
        args.seeds,
        args.test_size,
        args.top_n,
        args.random_ranking_trials,
    )

    model_zoo.to_csv(args.outdir / f"{args.output_prefix}_model_zoo_repeated.csv", index=False)
    feature_ablation.to_csv(args.outdir / f"{args.output_prefix}_feature_ablation.csv", index=False)
    learning_curve.to_csv(args.outdir / f"{args.output_prefix}_learning_curve.csv", index=False)
    corner_holdout.to_csv(args.outdir / f"{args.output_prefix}_corner_holdout.csv", index=False)
    transfer.to_csv(args.outdir / f"{args.output_prefix}_transfer_robustness.csv", index=False)
    ranking.to_csv(args.outdir / f"{args.output_prefix}_candidate_ranking_robustness.csv", index=False)
    write_report(
        df,
        model_zoo,
        feature_ablation,
        learning_curve,
        corner_holdout,
        transfer,
        ranking,
        args.outdir,
        args.output_prefix,
    )

    print(f"Rows used: {len(df)}")
    print(f"Wrote {args.outdir / f'{args.output_prefix}_robustness_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
