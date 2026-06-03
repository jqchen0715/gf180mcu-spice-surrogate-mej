#!/usr/bin/env python3
"""
Baseline and transfer experiments for the GF180MCU SPICE V2 dataset.

This script is intentionally modest: it establishes a reproducible first
benchmark for the Microelectronics Journal extension, not the final model zoo.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable
import warnings

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = PROJECT_ROOT / "data" / "dataset_v2_spice_320.csv"
DEFAULT_OUTDIR = PROJECT_ROOT / "results" / "v2"

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run V2 baseline and transfer experiments.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--fewshot-k", nargs="*", type=int, default=[0, 5, 10, 20, 40])
    return parser.parse_args()


def one_hot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", one_hot_encoder(), CATEGORICAL_FEATURES),
        ]
    )


def model_specs(random_state: int) -> dict[str, object]:
    return {
        "Ridge": Ridge(alpha=1.0),
        "RandomForest": RandomForestRegressor(
            n_estimators=250,
            min_samples_leaf=2,
            random_state=random_state,
            n_jobs=-1,
        ),
        "GradientBoosting": GradientBoostingRegressor(random_state=random_state),
        "MLP": MLPRegressor(
            hidden_layer_sizes=(96, 48),
            activation="relu",
            alpha=1e-4,
            learning_rate_init=1e-3,
            max_iter=2000,
            early_stopping=True,
            validation_fraction=0.15,
            random_state=random_state,
        ),
    }


def metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    mae = mean_absolute_error(y_true, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2 = r2_score(y_true, y_pred)
    denom = np.maximum(np.abs(y_true), 1e-12)
    mape = float(np.mean(np.abs((y_true - y_pred) / denom)) * 100)
    return {"r2": float(r2), "mae": float(mae), "rmse": rmse, "mape_pct": mape}


def fit_predict(model, train: pd.DataFrame, test: pd.DataFrame, target: str) -> tuple[np.ndarray, Pipeline]:
    pipe = Pipeline([("pre", preprocessor()), ("model", model)])
    pipe.fit(train[NUMERIC_FEATURES + CATEGORICAL_FEATURES], train[target])
    pred = pipe.predict(test[NUMERIC_FEATURES + CATEGORICAL_FEATURES])
    return pred, pipe


def run_random_split(df: pd.DataFrame, random_state: int, test_size: float) -> list[dict[str, object]]:
    train, test = train_test_split(
        df,
        test_size=test_size,
        random_state=random_state,
        stratify=df["cell_type"],
    )
    rows: list[dict[str, object]] = []

    for target in TARGETS:
        for model_name, model in model_specs(random_state).items():
            pred, _ = fit_predict(model, train, test, target)
            row = {
                "experiment": "random_split",
                "target": target,
                "model": model_name,
                "train_rows": len(train),
                "test_rows": len(test),
                "heldout_cell": "",
                "fewshot_k": "",
            }
            row.update(metrics(test[target].to_numpy(), pred))
            rows.append(row)
    return rows


def sample_target_cell(df: pd.DataFrame, cell: str, k: int, random_state: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    target_df = df[df["cell_type"] == cell]
    if k <= 0:
        return target_df.iloc[0:0].copy(), target_df.copy()
    support = target_df.sample(n=min(k, len(target_df) - 1), random_state=random_state)
    query = target_df.drop(index=support.index)
    return support, query


def run_cell_transfer(df: pd.DataFrame, random_state: int, fewshot_k: Iterable[int]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    cells = sorted(df["cell_type"].unique())

    for heldout_cell in cells:
        source = df[df["cell_type"] != heldout_cell]
        for k in fewshot_k:
            support, query = sample_target_cell(df, heldout_cell, k, random_state + k)
            for target in TARGETS:
                transfer_train = pd.concat([source, support], ignore_index=True)
                for model_name in ["RandomForest", "GradientBoosting", "MLP"]:
                    model = model_specs(random_state)[model_name]
                    pred, _ = fit_predict(model, transfer_train, query, target)
                    row = {
                        "experiment": "cell_transfer",
                        "target": target,
                        "model": model_name,
                        "train_rows": len(transfer_train),
                        "test_rows": len(query),
                        "heldout_cell": heldout_cell,
                        "fewshot_k": k,
                    }
                    row.update(metrics(query[target].to_numpy(), pred))
                    rows.append(row)

                if k > 0:
                    for model_name in ["RandomForest", "GradientBoosting"]:
                        model = model_specs(random_state)[model_name]
                        pred, _ = fit_predict(model, support, query, target)
                        row = {
                            "experiment": "cell_fewshot_from_scratch",
                            "target": target,
                            "model": model_name,
                            "train_rows": len(support),
                            "test_rows": len(query),
                            "heldout_cell": heldout_cell,
                            "fewshot_k": k,
                        }
                        row.update(metrics(query[target].to_numpy(), pred))
                        rows.append(row)
    return rows


def load_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = set(NUMERIC_FEATURES + CATEGORICAL_FEATURES + TARGETS + ["status", "fidelity"])
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}")

    df = df[(df["status"] == "ok") & (df["fidelity"] == "SPICE_GF180MCU")].copy()
    if df.empty:
        raise ValueError("No publication-eligible SPICE_GF180MCU rows found.")
    return df


def write_report(df: pd.DataFrame, results: pd.DataFrame, outdir: Path) -> None:
    report_path = outdir / "v2_baseline_transfer_report.md"
    best_random = (
        results[results["experiment"] == "random_split"]
        .sort_values(["target", "r2"], ascending=[True, False])
        .groupby("target")
        .head(1)
    )
    transfer = results[results["experiment"] == "cell_transfer"].copy()
    transfer["fewshot_k"] = pd.to_numeric(transfer["fewshot_k"], errors="coerce").astype(int)
    scratch = results[results["experiment"] == "cell_fewshot_from_scratch"].copy()
    scratch["fewshot_k"] = pd.to_numeric(scratch["fewshot_k"], errors="coerce").astype(int)
    best_transfer_by_k = (
        transfer.sort_values(
            ["target", "heldout_cell", "fewshot_k", "r2"],
            ascending=[True, True, True, False],
        )
        .groupby(["target", "heldout_cell", "fewshot_k"])
        .head(1)
    )
    transfer_k_summary = (
        best_transfer_by_k.groupby(["target", "fewshot_k"])
        .agg(
            median_r2=("r2", "median"),
            min_r2=("r2", "min"),
            median_mae=("mae", "median"),
            median_mape_pct=("mape_pct", "median"),
        )
        .reset_index()
    )
    best_scratch_by_k = (
        scratch.sort_values(
            ["target", "heldout_cell", "fewshot_k", "r2"],
            ascending=[True, True, True, False],
        )
        .groupby(["target", "heldout_cell", "fewshot_k"])
        .head(1)
    )
    scratch_k_summary = (
        best_scratch_by_k.groupby(["target", "fewshot_k"])
        .agg(
            median_r2=("r2", "median"),
            min_r2=("r2", "min"),
            median_mae=("mae", "median"),
            median_mape_pct=("mape_pct", "median"),
        )
        .reset_index()
    )
    transfer_gain = transfer_k_summary.merge(
        scratch_k_summary,
        on=["target", "fewshot_k"],
        suffixes=("_transfer", "_scratch"),
    )
    transfer_gain["median_r2_gain"] = (
        transfer_gain["median_r2_transfer"] - transfer_gain["median_r2_scratch"]
    )
    zero_shot_best = best_transfer_by_k[best_transfer_by_k["fewshot_k"] == 0][
        ["target", "heldout_cell", "model", "r2", "mae", "rmse", "mape_pct"]
    ]

    lines = [
        "# V2 Baseline and Transfer Report",
        "",
        "## Dataset",
        "",
        f"- Rows used: {len(df)}",
        f"- Cells: {', '.join(sorted(df['cell_type'].unique()))}",
        f"- Fidelity: {', '.join(sorted(df['fidelity'].unique()))}",
        f"- Status values: {', '.join(sorted(df['status'].unique()))}",
        "",
        "## Best Random-Split Models",
        "",
        markdown_table(best_random[["target", "model", "r2", "mae", "rmse", "mape_pct"]]),
        "",
        "## Transfer Protocol",
        "",
        "Leave-one-cell-out transfer is evaluated with k-shot support samples from the target cell.",
        "Rows with k=0 are zero-shot transfer results.",
        "From-scratch few-shot baselines are trained only on the k target-cell support samples and are reported for k>0.",
        "",
        "## Transfer Summary",
        "",
        markdown_table(transfer_k_summary),
        "",
        "## From-Scratch Few-Shot Summary",
        "",
        markdown_table(scratch_k_summary),
        "",
        "## Transfer vs From-Scratch Gain",
        "",
        markdown_table(
            transfer_gain[
                [
                    "target",
                    "fewshot_k",
                    "median_r2_transfer",
                    "median_r2_scratch",
                    "median_r2_gain",
                    "median_mae_transfer",
                    "median_mae_scratch",
                ]
            ]
        ),
        "",
        "## Zero-Shot Best Models by Held-Out Cell",
        "",
        markdown_table(zero_shot_best),
        "",
        "## Output Files",
        "",
        "- `v2_baseline_transfer_results.csv`",
        "- `v2_dataset_summary.json`",
    ]

    summary = {
        "rows_used": int(len(df)),
        "cells": sorted(df["cell_type"].unique().tolist()),
        "targets": TARGETS,
        "random_split_best": best_random.to_dict(orient="records"),
        "transfer_rows": int(len(transfer)),
        "scratch_rows": int(len(scratch)),
        "transfer_k_summary": transfer_k_summary.to_dict(orient="records"),
        "scratch_k_summary": scratch_k_summary.to_dict(orient="records"),
        "transfer_gain": transfer_gain.to_dict(orient="records"),
        "zero_shot_best": zero_shot_best.to_dict(orient="records"),
    }
    (outdir / "v2_dataset_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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


def main() -> int:
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=RuntimeWarning)

    df = load_dataset(args.dataset)
    results = pd.DataFrame(
        run_random_split(df, args.random_state, args.test_size)
        + run_cell_transfer(df, args.random_state, args.fewshot_k)
    )
    results_path = args.outdir / "v2_baseline_transfer_results.csv"
    results.to_csv(results_path, index=False)
    write_report(df, results, args.outdir)

    print(f"Rows used: {len(df)}")
    print(f"Cells: {', '.join(sorted(df['cell_type'].unique()))}")
    print(f"Wrote {results_path}")
    print(f"Wrote {args.outdir / 'v2_baseline_transfer_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
