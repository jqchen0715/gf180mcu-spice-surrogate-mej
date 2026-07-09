#!/usr/bin/env python3
"""Enhanced evaluation package for the SCI resubmission manuscript.

This script adds reviewer-facing checks that were missing from the rejected
version: stronger tabular baselines, statistical tests, ranking metrics,
conformal prediction intervals, feature-importance summaries, and measured
training/inference/SPICE runtime summaries.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import time
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    ExtraTreesRegressor,
    GradientBoostingRegressor,
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVR

try:
    from xgboost import XGBRegressor
except Exception:  # pragma: no cover - optional dependency
    XGBRegressor = None

try:
    from lightgbm import LGBMRegressor
except Exception:  # pragma: no cover - optional dependency
    LGBMRegressor = None

try:
    from catboost import CatBoostRegressor
except Exception:  # pragma: no cover - optional dependency
    CatBoostRegressor = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_V2 = PROJECT_ROOT / "data" / "dataset_v2_spice_320.csv"
DEFAULT_V3 = PROJECT_ROOT / "data" / "dataset_v3_spice_480.csv"
DEFAULT_OUTDIR = PROJECT_ROOT / "results" / "sci_revision"

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
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
TARGETS = ["delay_avg_ns", "power_avg_uW"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run enhanced SCI revision evaluations.")
    parser.add_argument("--v2", type=Path, default=DEFAULT_V2)
    parser.add_argument("--v3", type=Path, default=DEFAULT_V3)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--seeds", nargs="*", type=int, default=list(range(20)))
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--ranking-top-fraction", type=float, default=0.2)
    parser.add_argument("--conformal-alpha", type=float, default=0.10)
    parser.add_argument("--permutation-repeats", type=int, default=10)
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


def load_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = set(FEATURES + TARGETS + ["status", "fidelity", "log_path"])
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"{path} is missing required columns: {missing}")
    df = df[(df["status"] == "ok") & (df["fidelity"] == "SPICE_GF180MCU")].copy()
    if df.empty:
        raise ValueError(f"{path} has no publication-eligible SPICE rows.")
    return df.reset_index(drop=True)


def model_specs(seed: int) -> dict[str, Any]:
    specs: dict[str, Any] = {
        "Ridge": Ridge(alpha=1.0),
        "SVR_RBF": SVR(kernel="rbf", C=10.0, epsilon=0.01),
        "GaussianProcess": GaussianProcessRegressor(
            kernel=ConstantKernel(1.0) * Matern(length_scale=1.0, nu=1.5)
            + WhiteKernel(noise_level=1e-5),
            normalize_y=True,
            random_state=seed,
            n_restarts_optimizer=0,
            alpha=1e-8,
        ),
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
    if XGBRegressor is not None:
        specs["XGBoost"] = XGBRegressor(
            n_estimators=300,
            max_depth=3,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="reg:squarederror",
            random_state=seed,
            n_jobs=1,
            verbosity=0,
        )
    if LGBMRegressor is not None:
        specs["LightGBM"] = LGBMRegressor(
            n_estimators=300,
            max_depth=4,
            num_leaves=15,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=seed,
            n_jobs=1,
            verbose=-1,
        )
    if CatBoostRegressor is not None:
        specs["CatBoost"] = CatBoostRegressor(
            iterations=300,
            depth=4,
            learning_rate=0.05,
            loss_function="RMSE",
            random_seed=seed,
            verbose=False,
            allow_writing_files=False,
        )
    return specs


def build_pipeline(model: Any) -> Pipeline:
    return Pipeline([("pre", preprocessor()), ("model", model)])


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    abs_err = np.abs(y_true - y_pred)
    denom = np.maximum(np.abs(y_true), 1e-12)
    return {
        "r2": float(r2_score(y_true, y_pred)),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mape_pct": float(np.mean(abs_err / denom) * 100),
        "p90_abs_err": float(np.quantile(abs_err, 0.90)),
        "p95_abs_err": float(np.quantile(abs_err, 0.95)),
        "max_abs_err": float(np.max(abs_err)),
    }


def fit_predict_timed(
    train: pd.DataFrame,
    test: pd.DataFrame,
    target: str,
    model_name: str,
    seed: int,
) -> tuple[np.ndarray, float, float, Pipeline]:
    pipe = build_pipeline(model_specs(seed)[model_name])
    t0 = time.perf_counter()
    pipe.fit(train[FEATURES], train[target])
    fit_seconds = time.perf_counter() - t0
    t1 = time.perf_counter()
    pred = pipe.predict(test[FEATURES])
    predict_seconds = time.perf_counter() - t1
    return pred, fit_seconds, predict_seconds, pipe


def run_model_zoo(v2: pd.DataFrame, seeds: list[int], test_size: float) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for seed in seeds:
        train, test = train_test_split(
            v2,
            test_size=test_size,
            random_state=seed,
            stratify=v2["cell_type"],
        )
        for target in TARGETS:
            for model_name in model_specs(seed):
                pred, fit_seconds, predict_seconds, _ = fit_predict_timed(
                    train, test, target, model_name, seed
                )
                row: dict[str, Any] = {
                    "seed": seed,
                    "target": target,
                    "model": model_name,
                    "train_rows": len(train),
                    "test_rows": len(test),
                    "fit_seconds": fit_seconds,
                    "predict_seconds": predict_seconds,
                    "predict_us_per_row": predict_seconds / max(len(test), 1) * 1e6,
                }
                row.update(regression_metrics(test[target].to_numpy(), pred))
                rows.append(row)
    return pd.DataFrame(rows)


def summarize_model_zoo(results: pd.DataFrame) -> pd.DataFrame:
    return (
        results.groupby(["target", "model"])
        .agg(
            runs=("r2", "count"),
            median_r2=("r2", "median"),
            q25_r2=("r2", lambda s: float(s.quantile(0.25))),
            q75_r2=("r2", lambda s: float(s.quantile(0.75))),
            median_mae=("mae", "median"),
            median_p95_abs_err=("p95_abs_err", "median"),
            median_max_abs_err=("max_abs_err", "median"),
            median_fit_seconds=("fit_seconds", "median"),
            median_predict_us_per_row=("predict_us_per_row", "median"),
        )
        .reset_index()
    )


def run_external_validation_all_models(v2: pd.DataFrame, v3: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for target in TARGETS:
        for model_name in model_specs(0):
            pred, fit_seconds, predict_seconds, _ = fit_predict_timed(v2, v3, target, model_name, 0)
            row: dict[str, Any] = {
                "experiment": "v2_train_v3_external_validation",
                "target": target,
                "model": model_name,
                "train_rows": len(v2),
                "test_rows": len(v3),
                "fit_seconds": fit_seconds,
                "predict_seconds": predict_seconds,
                "predict_us_per_row": predict_seconds / max(len(v3), 1) * 1e6,
            }
            row.update(regression_metrics(v3[target].to_numpy(), pred))
            rows.append(row)
    return pd.DataFrame(rows)


def summarize_external_validation(external: pd.DataFrame) -> pd.DataFrame:
    return (
        external.sort_values(["target", "r2"], ascending=[True, False])
        .groupby("target")
        .head(6)
        .reset_index(drop=True)
    )


def run_stat_tests(results: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    friedman_rows: list[dict[str, Any]] = []
    wilcoxon_rows: list[dict[str, Any]] = []
    for target in TARGETS:
        subset = results[results["target"] == target].copy()
        pivot_r2 = subset.pivot(index="seed", columns="model", values="r2").dropna(axis=1)
        pivot_mae = subset.pivot(index="seed", columns="model", values="mae").dropna(axis=1)
        if pivot_r2.shape[1] >= 3:
            stat, pvalue = stats.friedmanchisquare(
                *[pivot_r2[col].to_numpy() for col in pivot_r2.columns]
            )
            avg_ranks = pivot_r2.rank(axis=1, ascending=False).mean().to_dict()
            friedman_rows.append(
                {
                    "target": target,
                    "models": ", ".join(pivot_r2.columns),
                    "friedman_stat": float(stat),
                    "friedman_p": float(pvalue),
                    "best_avg_rank_model": min(avg_ranks, key=avg_ranks.get),
                    "best_avg_rank": float(min(avg_ranks.values())),
                }
            )
        if pivot_mae.shape[1] >= 2:
            best_model = pivot_mae.median(axis=0).idxmin()
            raw: list[tuple[str, float]] = []
            for other in pivot_mae.columns:
                if other == best_model:
                    continue
                try:
                    stat, pvalue = stats.wilcoxon(
                        pivot_mae[best_model],
                        pivot_mae[other],
                        zero_method="wilcox",
                        alternative="two-sided",
                    )
                except ValueError:
                    stat, pvalue = np.nan, 1.0
                raw.append((other, float(pvalue)))
                wilcoxon_rows.append(
                    {
                        "target": target,
                        "best_median_mae_model": best_model,
                        "comparison_model": other,
                        "median_mae_best": float(pivot_mae[best_model].median()),
                        "median_mae_other": float(pivot_mae[other].median()),
                        "wilcoxon_stat": float(stat) if not np.isnan(stat) else np.nan,
                        "wilcoxon_p_raw": float(pvalue),
                    }
                )
            m = len(raw)
            sorted_pairs = sorted(raw, key=lambda item: item[1])
            adjusted: dict[str, float] = {}
            for rank, (model_name, pvalue) in enumerate(sorted_pairs):
                adjusted[model_name] = min((m - rank) * pvalue, 1.0)
            for row in wilcoxon_rows:
                if row["target"] == target and row["comparison_model"] in adjusted:
                    row["wilcoxon_p_holm"] = adjusted[row["comparison_model"]]
    return pd.DataFrame(friedman_rows), pd.DataFrame(wilcoxon_rows)


def normalized_score(df: pd.DataFrame, delay_col: str, power_col: str) -> pd.Series:
    delay_range = max(df[delay_col].max() - df[delay_col].min(), 1e-12)
    power_range = max(df[power_col].max() - df[power_col].min(), 1e-12)
    delay_norm = (df[delay_col] - df[delay_col].min()) / delay_range
    power_norm = (df[power_col] - df[power_col].min()) / power_range
    return 0.5 * delay_norm + 0.5 * power_norm


def ndcg_at_k(relevance: np.ndarray, order: np.ndarray, k: int) -> float:
    k = min(k, len(order))
    rel = relevance[order[:k]]
    discounts = 1.0 / np.log2(np.arange(2, k + 2))
    dcg = float(np.sum(rel * discounts))
    ideal = np.sort(relevance)[::-1][:k]
    idcg = float(np.sum(ideal * discounts))
    return dcg / idcg if idcg > 0 else 0.0


def ranking_metrics_from_predictions(df: pd.DataFrame, selected_k: int) -> dict[str, float]:
    pred_score = df["pred_score"].to_numpy()
    actual_score = df["actual_score"].to_numpy()
    pred_order = np.argsort(pred_score)
    actual_order = np.argsort(actual_score)
    n = len(df)
    top10 = max(1, math.ceil(n * 0.10))
    top20 = max(1, math.ceil(n * 0.20))
    selected_k = min(selected_k, n)
    selected = set(pred_order[:selected_k])
    actual_top10 = set(actual_order[:top10])
    actual_top20 = set(actual_order[:top20])
    relevance = 1.0 - (actual_score - actual_score.min()) / max(actual_score.max() - actual_score.min(), 1e-12)
    return {
        "pool_rows": float(n),
        "selected_k": float(selected_k),
        "spearman": float(stats.spearmanr(pred_score, actual_score).statistic),
        "kendall_tau": float(stats.kendalltau(pred_score, actual_score).statistic),
        "precision_at_k_top10": float(len(selected & actual_top10) / selected_k),
        "recall_at_k_top10": float(len(selected & actual_top10) / top10),
        "precision_at_k_top20": float(len(selected & actual_top20) / selected_k),
        "recall_at_k_top20": float(len(selected & actual_top20) / top20),
        "ndcg_at_k": ndcg_at_k(relevance, pred_order, selected_k),
        "median_actual_rank_selected": float(
            pd.Series(actual_score).rank(method="min", ascending=True).iloc[list(selected)].median()
        ),
    }


def run_ranking_metrics(
    v2: pd.DataFrame,
    v3: pd.DataFrame,
    seeds: list[int],
    test_size: float,
    top_fraction: float,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for seed in seeds:
        train, test = train_test_split(
            v2,
            test_size=test_size,
            random_state=seed,
            stratify=v2["cell_type"],
        )
        pred_df = test.copy().reset_index(drop=True)
        for target in TARGETS:
            pred, _, _, _ = fit_predict_timed(train, test, target, "GradientBoosting", seed)
            pred_df[f"pred_{target}"] = pred
        pred_df["pred_score"] = normalized_score(pred_df, "pred_delay_avg_ns", "pred_power_avg_uW")
        pred_df["actual_score"] = normalized_score(pred_df, "delay_avg_ns", "power_avg_uW")
        selected_k = max(1, math.ceil(len(pred_df) * top_fraction))
        row = {
            "experiment": "v2_repeated_holdout",
            "seed": seed,
        }
        row.update(ranking_metrics_from_predictions(pred_df, selected_k))
        rows.append(row)

    v3_pred = v3.copy().reset_index(drop=True)
    for target in TARGETS:
        pred, _, _, _ = fit_predict_timed(v2, v3, target, "GradientBoosting", 0)
        v3_pred[f"pred_{target}"] = pred
    v3_pred["pred_score"] = normalized_score(v3_pred, "pred_delay_avg_ns", "pred_power_avg_uW")
    v3_pred["actual_score"] = normalized_score(v3_pred, "delay_avg_ns", "power_avg_uW")
    selected_k = max(1, math.ceil(len(v3_pred) * top_fraction))
    row = {
        "experiment": "v2_train_v3_validation",
        "seed": "",
    }
    row.update(ranking_metrics_from_predictions(v3_pred, selected_k))
    rows.append(row)
    return pd.DataFrame(rows)


def conformal_quantile(residuals: np.ndarray, alpha: float) -> float:
    n = len(residuals)
    if n == 0:
        return float("nan")
    level = min(math.ceil((n + 1) * (1 - alpha)) / n, 1.0)
    return float(np.quantile(residuals, level, method="higher"))


def run_conformal_intervals(
    v2: pd.DataFrame,
    v3: pd.DataFrame,
    seeds: list[int],
    alpha: float,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for seed in seeds:
        train_cal, test = train_test_split(
            v2,
            test_size=0.2,
            random_state=seed,
            stratify=v2["cell_type"],
        )
        train, cal = train_test_split(
            train_cal,
            test_size=0.25,
            random_state=seed + 1000,
            stratify=train_cal["cell_type"],
        )
        for target in TARGETS:
            cal_pred, _, _, pipe = fit_predict_timed(train, cal, target, "GradientBoosting", seed)
            q = conformal_quantile(np.abs(cal[target].to_numpy() - cal_pred), alpha)
            test_pred = pipe.predict(test[FEATURES])
            abs_err = np.abs(test[target].to_numpy() - test_pred)
            rows.append(
                {
                    "experiment": "v2_split_conformal",
                    "seed": seed,
                    "target": target,
                    "model": "GradientBoosting",
                    "train_rows": len(train),
                    "calibration_rows": len(cal),
                    "test_rows": len(test),
                    "nominal_coverage": 1 - alpha,
                    "empirical_coverage": float(np.mean(abs_err <= q)),
                    "interval_width": float(2 * q),
                    "median_abs_err": float(np.median(abs_err)),
                    "p95_abs_err": float(np.quantile(abs_err, 0.95)),
                }
            )

    train, cal = train_test_split(
        v2,
        test_size=0.30,
        random_state=2026,
        stratify=v2["cell_type"],
    )
    for target in TARGETS:
        cal_pred, _, _, pipe = fit_predict_timed(train, cal, target, "GradientBoosting", 2026)
        q = conformal_quantile(np.abs(cal[target].to_numpy() - cal_pred), alpha)
        v3_pred = pipe.predict(v3[FEATURES])
        abs_err = np.abs(v3[target].to_numpy() - v3_pred)
        rows.append(
            {
                "experiment": "v2_calibrated_v3_external",
                "seed": "",
                "target": target,
                "model": "GradientBoosting",
                "train_rows": len(train),
                "calibration_rows": len(cal),
                "test_rows": len(v3),
                "nominal_coverage": 1 - alpha,
                "empirical_coverage": float(np.mean(abs_err <= q)),
                "interval_width": float(2 * q),
                "median_abs_err": float(np.median(abs_err)),
                "p95_abs_err": float(np.quantile(abs_err, 0.95)),
            }
        )
    return pd.DataFrame(rows)


def run_feature_importance(v2: pd.DataFrame, repeats: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    train, test = train_test_split(
        v2,
        test_size=0.2,
        random_state=42,
        stratify=v2["cell_type"],
    )
    for target in TARGETS:
        pipe = build_pipeline(GradientBoostingRegressor(random_state=42))
        pipe.fit(train[FEATURES], train[target])
        result = permutation_importance(
            pipe,
            test[FEATURES],
            test[target],
            n_repeats=repeats,
            random_state=42,
            scoring="r2",
        )
        for feature, mean_imp, std_imp in zip(FEATURES, result.importances_mean, result.importances_std):
            rows.append(
                {
                    "target": target,
                    "model": "GradientBoosting",
                    "feature": feature,
                    "importance_mean_delta_r2": float(mean_imp),
                    "importance_std_delta_r2": float(std_imp),
                }
            )
    return pd.DataFrame(rows)


def parse_spice_runtime(dataset: pd.DataFrame) -> pd.DataFrame:
    pattern = re.compile(r"Total elapsed time \(seconds\)\s*=\s*([0-9.]+)")
    rows: list[dict[str, Any]] = []
    for _, row in dataset.iterrows():
        log_path = PROJECT_ROOT / str(row["log_path"])
        if not log_path.exists():
            continue
        text = log_path.read_text(errors="ignore")
        match = pattern.search(text)
        if not match:
            continue
        rows.append(
            {
                "sample_id": row["sample_id"],
                "cell_type": row["cell_type"],
                "dataset": "v3" if int(row["sample_id"]) >= 20000 else "v2",
                "elapsed_seconds": float(match.group(1)),
            }
        )
    return pd.DataFrame(rows)


def summarize_spice_runtime(runtime: pd.DataFrame) -> pd.DataFrame:
    if runtime.empty:
        return pd.DataFrame()
    by_dataset = (
        runtime.groupby("dataset")
        .agg(
            rows=("elapsed_seconds", "count"),
            median_elapsed_s=("elapsed_seconds", "median"),
            p90_elapsed_s=("elapsed_seconds", lambda s: float(s.quantile(0.90))),
            total_elapsed_s=("elapsed_seconds", "sum"),
        )
        .reset_index()
    )
    by_cell = (
        runtime.groupby(["dataset", "cell_type"])
        .agg(
            rows=("elapsed_seconds", "count"),
            median_elapsed_s=("elapsed_seconds", "median"),
            total_elapsed_s=("elapsed_seconds", "sum"),
        )
        .reset_index()
    )
    return pd.concat(
        [
            by_dataset.assign(group="dataset", cell_type=""),
            by_cell.assign(group="dataset_cell"),
        ],
        ignore_index=True,
        sort=False,
    )


def summarize_ranking(ranking: pd.DataFrame) -> pd.DataFrame:
    numeric_cols = [
        "spearman",
        "kendall_tau",
        "precision_at_k_top10",
        "recall_at_k_top10",
        "precision_at_k_top20",
        "recall_at_k_top20",
        "ndcg_at_k",
        "median_actual_rank_selected",
    ]
    return (
        ranking.groupby("experiment")[numeric_cols]
        .median()
        .reset_index()
        .rename(columns={col: f"median_{col}" for col in numeric_cols})
    )


def summarize_conformal(conformal: pd.DataFrame) -> pd.DataFrame:
    return (
        conformal.groupby(["experiment", "target"])
        .agg(
            runs=("empirical_coverage", "count"),
            median_empirical_coverage=("empirical_coverage", "median"),
            q25_empirical_coverage=("empirical_coverage", lambda s: float(s.quantile(0.25))),
            q75_empirical_coverage=("empirical_coverage", lambda s: float(s.quantile(0.75))),
            median_interval_width=("interval_width", "median"),
            median_abs_err=("median_abs_err", "median"),
            median_p95_abs_err=("p95_abs_err", "median"),
        )
        .reset_index()
    )


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows available._"
    rendered = df.copy()
    for col in rendered.columns:
        if pd.api.types.is_numeric_dtype(rendered[col]):
            rendered[col] = rendered[col].map(lambda x: f"{x:.4g}")
        else:
            rendered[col] = rendered[col].astype(str)
    header = "| " + " | ".join(rendered.columns) + " |"
    sep = "| " + " | ".join(["---"] * len(rendered.columns)) + " |"
    rows = ["| " + " | ".join(row) + " |" for row in rendered.astype(str).to_numpy()]
    return "\n".join([header, sep] + rows)


def write_report(
    v2: pd.DataFrame,
    v3: pd.DataFrame,
    model_summary: pd.DataFrame,
    external_summary: pd.DataFrame,
    friedman: pd.DataFrame,
    wilcoxon: pd.DataFrame,
    ranking_summary: pd.DataFrame,
    conformal_summary: pd.DataFrame,
    importance: pd.DataFrame,
    runtime_summary: pd.DataFrame,
    outdir: Path,
) -> None:
    best_models = (
        model_summary.sort_values(["target", "median_r2"], ascending=[True, False])
        .groupby("target")
        .head(6)
        .reset_index(drop=True)
    )
    top_importance = (
        importance.sort_values(["target", "importance_mean_delta_r2"], ascending=[True, False])
        .groupby("target")
        .head(8)
        .reset_index(drop=True)
    )
    key_wilcoxon = wilcoxon.sort_values(["target", "wilcoxon_p_holm"]).groupby("target").head(6)
    lines = [
        "# SCI Revision Enhanced Evaluation",
        "",
        "## Dataset",
        "",
        f"- Primary SPICE rows: {len(v2)}.",
        f"- Validation SPICE rows: {len(v3)}.",
        f"- Cells: {', '.join(sorted(v2['cell_type'].unique()))}.",
        f"- Modern optional baselines included: XGBoost={XGBRegressor is not None}, LightGBM={LGBMRegressor is not None}, CatBoost={CatBoostRegressor is not None}.",
        "",
        "## Stronger Tabular Baselines and Cost",
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
                    "median_mae",
                    "median_p95_abs_err",
                    "median_fit_seconds",
                    "median_predict_us_per_row",
                ]
            ]
        ),
        "",
        "## Primary-to-Validation Generalization",
        "",
        markdown_table(
            external_summary[
                [
                    "target",
                    "model",
                    "r2",
                    "mae",
                    "p95_abs_err",
                    "max_abs_err",
                    "fit_seconds",
                    "predict_us_per_row",
                ]
            ]
        ),
        "",
        "## Statistical Tests",
        "",
        "Friedman tests use repeated-split R2 values across all complete model columns. Wilcoxon tests compare the best median-MAE model with each alternative on paired split MAE values with Holm adjustment.",
        "",
        markdown_table(friedman),
        "",
        markdown_table(
            key_wilcoxon[
                [
                    "target",
                    "best_median_mae_model",
                    "comparison_model",
                    "median_mae_best",
                    "median_mae_other",
                    "wilcoxon_p_raw",
                    "wilcoxon_p_holm",
                ]
            ]
        ),
        "",
        "## Ranking Metrics",
        "",
        markdown_table(ranking_summary),
        "",
        "## Conformal Prediction Intervals",
        "",
        markdown_table(conformal_summary),
        "",
        "## Permutation Feature Importance",
        "",
        markdown_table(top_importance),
        "",
        "## Parsed SPICE Runtime",
        "",
        markdown_table(runtime_summary),
        "",
        "## Boundary Note",
        "",
        "The enhanced evaluation strengthens tabular surrogate evidence. It does not establish graph-based, cross-PDK, layout-extracted, or online simulator-in-the-loop active learning claims.",
    ]
    (outdir / "sci_revision_enhanced_evaluation_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    args.outdir.mkdir(parents=True, exist_ok=True)

    v2 = load_dataset(args.v2)
    v3 = load_dataset(args.v3)

    model_zoo = run_model_zoo(v2, args.seeds, args.test_size)
    model_summary = summarize_model_zoo(model_zoo)
    external = run_external_validation_all_models(v2, v3)
    external_summary = summarize_external_validation(external)
    friedman, wilcoxon = run_stat_tests(model_zoo)
    ranking = run_ranking_metrics(v2, v3, args.seeds, args.test_size, args.ranking_top_fraction)
    ranking_summary = summarize_ranking(ranking)
    conformal = run_conformal_intervals(v2, v3, args.seeds, args.conformal_alpha)
    conformal_summary = summarize_conformal(conformal)
    importance = run_feature_importance(v2, args.permutation_repeats)
    runtime = parse_spice_runtime(pd.concat([v2, v3], ignore_index=True))
    runtime_summary = summarize_spice_runtime(runtime)

    model_zoo.to_csv(args.outdir / "sci_model_zoo_repeated.csv", index=False)
    model_summary.to_csv(args.outdir / "sci_model_zoo_summary.csv", index=False)
    external.to_csv(args.outdir / "sci_external_validation_all_models.csv", index=False)
    external_summary.to_csv(args.outdir / "sci_external_validation_all_models_summary.csv", index=False)
    friedman.to_csv(args.outdir / "sci_friedman_tests.csv", index=False)
    wilcoxon.to_csv(args.outdir / "sci_wilcoxon_tests.csv", index=False)
    ranking.to_csv(args.outdir / "sci_ranking_metrics.csv", index=False)
    ranking_summary.to_csv(args.outdir / "sci_ranking_metrics_summary.csv", index=False)
    conformal.to_csv(args.outdir / "sci_conformal_intervals.csv", index=False)
    conformal_summary.to_csv(args.outdir / "sci_conformal_intervals_summary.csv", index=False)
    importance.to_csv(args.outdir / "sci_permutation_feature_importance.csv", index=False)
    runtime.to_csv(args.outdir / "sci_spice_runtime_parsed.csv", index=False)
    runtime_summary.to_csv(args.outdir / "sci_spice_runtime_summary.csv", index=False)
    (args.outdir / "sci_revision_enhanced_summary.json").write_text(
        json.dumps(
            {
                "v2_rows": int(len(v2)),
                "v3_rows": int(len(v3)),
                "models": sorted(model_zoo["model"].unique().tolist()),
                "targets": TARGETS,
                "best_models": model_summary.sort_values(["target", "median_r2"], ascending=[True, False])
                .groupby("target")
                .head(3)
                .to_dict(orient="records"),
                "external_validation": external_summary.to_dict(orient="records"),
                "ranking": ranking_summary.to_dict(orient="records"),
                "conformal": conformal_summary.to_dict(orient="records"),
                "spice_runtime": runtime_summary.to_dict(orient="records"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    write_report(
        v2,
        v3,
        model_summary,
        external_summary,
        friedman,
        wilcoxon,
        ranking_summary,
        conformal_summary,
        importance,
        runtime_summary,
        args.outdir,
    )
    print(f"Primary rows: {len(v2)}")
    print(f"Validation rows: {len(v3)}")
    print(f"Models: {', '.join(sorted(model_zoo['model'].unique()))}")
    print(f"Wrote {args.outdir / 'sci_revision_enhanced_evaluation_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
