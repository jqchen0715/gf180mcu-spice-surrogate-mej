#!/usr/bin/env python3
"""Model diagnostics and SPICE-measured design-space exploration for the primary SPICE dataset."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import warnings

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = PROJECT_ROOT / "data" / "dataset_v2_spice_320.csv"
DEFAULT_OUTDIR = PROJECT_ROOT / "results" / "v2_diagnostics"
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
    parser = argparse.ArgumentParser(description="Run primary-dataset diagnostic figures and Pareto case study.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--test-size", type=float, default=0.2)
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


def model(random_state: int) -> Pipeline:
    return Pipeline(
        [
            ("pre", preprocessor()),
            ("model", GradientBoostingRegressor(random_state=random_state)),
        ]
    )


def load_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = set(NUMERIC_FEATURES + CATEGORICAL_FEATURES + TARGETS + ["status", "fidelity"])
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Dataset is missing columns: {missing}")
    df = df[(df["status"] == "ok") & (df["fidelity"] == "SPICE_GF180MCU")].copy()
    if df.empty:
        raise ValueError("No publication-eligible primary SPICE rows found.")
    return df.reset_index(drop=True)


def metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2 = float(r2_score(y_true, y_pred))
    denom = np.maximum(np.abs(y_true), 1e-12)
    mape = float(np.mean(np.abs((y_true - y_pred) / denom)) * 100)
    return {"r2": r2, "mae": mae, "rmse": rmse, "mape_pct": mape}


def fit_models(train: pd.DataFrame, test: pd.DataFrame, random_state: int) -> tuple[pd.DataFrame, dict[str, Pipeline]]:
    pred = test.copy()
    models: dict[str, Pipeline] = {}
    for target in TARGETS:
        pipe = model(random_state)
        pipe.fit(train[NUMERIC_FEATURES + CATEGORICAL_FEATURES], train[target])
        models[target] = pipe
        pred[f"pred_{target}"] = pipe.predict(test[NUMERIC_FEATURES + CATEGORICAL_FEATURES])
        pred[f"abs_err_{target}"] = (pred[f"pred_{target}"] - pred[target]).abs()
        pred[f"pct_err_{target}"] = pred[f"abs_err_{target}"] / np.maximum(pred[target].abs(), 1e-12) * 100
    return pred, models


def pareto_front(df: pd.DataFrame, delay_col: str, power_col: str) -> pd.DataFrame:
    ordered = df.sort_values([delay_col, power_col]).copy()
    best_power = np.inf
    keep = []
    for _, row in ordered.iterrows():
        power = row[power_col]
        if power < best_power:
            keep.append(True)
            best_power = power
        else:
            keep.append(False)
    return ordered.loc[keep].copy()


def normalized_score(df: pd.DataFrame, delay_col: str, power_col: str) -> pd.Series:
    delay_range = max(df[delay_col].max() - df[delay_col].min(), 1e-12)
    power_range = max(df[power_col].max() - df[power_col].min(), 1e-12)
    delay_norm = (df[delay_col] - df[delay_col].min()) / delay_range
    power_norm = (df[power_col] - df[power_col].min()) / power_range
    return 0.5 * delay_norm + 0.5 * power_norm


def pareto_case_study(pred: pd.DataFrame, top_n: int = 12) -> tuple[pd.DataFrame, dict[str, float]]:
    pred = pred.copy()
    pred["pred_composite_score"] = normalized_score(pred, "pred_delay_avg_ns", "pred_power_avg_uW")
    pred["actual_composite_score"] = normalized_score(pred, "delay_avg_ns", "power_avg_uW")
    pred["actual_composite_rank"] = pred["actual_composite_score"].rank(method="min", ascending=True)
    top10_cut = max(1, int(np.ceil(len(pred) * 0.10)))
    top20_cut = max(1, int(np.ceil(len(pred) * 0.20)))

    pred_front = pareto_front(pred, "pred_delay_avg_ns", "pred_power_avg_uW")
    selected = pred.sort_values("pred_composite_score").head(top_n).copy()
    actual_front = pareto_front(pred, "delay_avg_ns", "power_avg_uW")
    actual_ids = set(actual_front["sample_id"].astype(str))
    selected["actual_pareto_member"] = selected["sample_id"].astype(str).isin(actual_ids)
    selected["actual_top10pct_member"] = selected["actual_composite_rank"] <= top10_cut
    selected["actual_top20pct_member"] = selected["actual_composite_rank"] <= top20_cut
    summary = {
        "predicted_front_size": float(len(pred_front)),
        "actual_front_size": float(len(actual_front)),
        "selected_candidates": float(len(selected)),
        "selected_actual_pareto_hits": float(selected["actual_pareto_member"].sum()),
        "selected_actual_pareto_hit_rate": float(selected["actual_pareto_member"].mean() if len(selected) else 0.0),
        "selected_actual_top10pct_hits": float(selected["actual_top10pct_member"].sum()),
        "selected_actual_top20pct_hits": float(selected["actual_top20pct_member"].sum()),
        "selected_median_actual_composite_rank": float(selected["actual_composite_rank"].median()),
        "front_overlap_rate": float(len(set(pred_front["sample_id"].astype(str)) & actual_ids) / max(len(actual_ids), 1)),
    }
    return selected, summary


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


def setup_matplotlib():
    Path("/private/tmp/matplotlib-cache").mkdir(parents=True, exist_ok=True)
    Path("/private/tmp/fontconfig-cache").mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/matplotlib-cache")
    os.environ.setdefault("XDG_CACHE_HOME", "/private/tmp/fontconfig-cache")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def plot_predicted_vs_spice(pred: pd.DataFrame, outdir: Path) -> None:
    plt = setup_matplotlib()
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    config = [
        ("delay_avg_ns", "pred_delay_avg_ns", "Average delay (ns)"),
        ("power_avg_uW", "pred_power_avg_uW", r"Average power ($\mu$W)"),
    ]
    colors = {"INV": "#1f77b4", "NAND2": "#ff7f0e", "NOR2": "#2ca02c", "XOR2": "#d62728"}
    for ax, (actual, predicted, label) in zip(axes, config):
        for cell, group in pred.groupby("cell_type"):
            ax.scatter(group[actual], group[predicted], s=32, alpha=0.8, label=cell, color=colors[cell])
        lo = min(pred[actual].min(), pred[predicted].min())
        hi = max(pred[actual].max(), pred[predicted].max())
        ax.plot([lo, hi], [lo, hi], color="black", linewidth=1, linestyle="--")
        ax.set_xlabel(f"SPICE {label}")
        ax.set_ylabel(f"Predicted {label}")
        ax.grid(True, alpha=0.25)
    axes[0].legend(frameon=False, loc="upper left")
    fig.suptitle("Predicted vs SPICE on held-out primary SPICE dataset rows")
    fig.tight_layout()
    fig.savefig(outdir / "v2_predicted_vs_spice.png", dpi=300, bbox_inches="tight")
    fig.savefig(outdir / "v2_predicted_vs_spice.pdf", bbox_inches="tight")


def plot_error_by_cell(pred: pd.DataFrame, outdir: Path) -> None:
    plt = setup_matplotlib()
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    cells = sorted(pred["cell_type"].unique())
    data_delay = [pred[pred["cell_type"] == cell]["pct_err_delay_avg_ns"] for cell in cells]
    data_power = [pred[pred["cell_type"] == cell]["pct_err_power_avg_uW"] for cell in cells]
    axes[0].boxplot(data_delay, tick_labels=cells, showfliers=False)
    axes[1].boxplot(data_power, tick_labels=cells, showfliers=False)
    axes[0].set_ylabel("Absolute percentage error (%)")
    axes[1].set_ylabel("Absolute percentage error (%)")
    axes[0].set_title("Delay error by cell")
    axes[1].set_title("Power error by cell")
    for ax in axes:
        ax.grid(True, axis="y", alpha=0.25)
        ax.set_xlabel("Held-out cell")
    fig.suptitle("Held-out prediction error by cell type")
    fig.tight_layout()
    fig.savefig(outdir / "v2_error_by_cell.png", dpi=300, bbox_inches="tight")
    fig.savefig(outdir / "v2_error_by_cell.pdf", bbox_inches="tight")


def plot_pareto(pred: pd.DataFrame, selected: pd.DataFrame, outdir: Path) -> None:
    plt = setup_matplotlib()
    fig, ax = plt.subplots(figsize=(6.3, 4.8))
    ax.scatter(pred["delay_avg_ns"], pred["power_avg_uW"], s=28, alpha=0.35, label="Held-out primary SPICE dataset rows")
    ax.scatter(
        selected["delay_avg_ns"],
        selected["power_avg_uW"],
        s=68,
        marker="*",
        color="#d62728",
        label="Surrogate-selected, SPICE-measured",
    )
    actual_front = pareto_front(pred, "delay_avg_ns", "power_avg_uW")
    ax.plot(actual_front["delay_avg_ns"], actual_front["power_avg_uW"], color="black", linewidth=1.5, label="Held-out primary Pareto front")
    ax.set_xlabel("SPICE average delay (ns)")
    ax.set_ylabel(r"SPICE average power ($\mu$W)")
    ax.set_title("Held-out primary SPICE candidate check")
    ax.grid(True, alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(outdir / "v2_spice_verified_pareto_case.png", dpi=300, bbox_inches="tight")
    fig.savefig(outdir / "v2_spice_verified_pareto_case.pdf", bbox_inches="tight")


def write_report(
    pred: pd.DataFrame,
    selected: pd.DataFrame,
    metric_rows: list[dict[str, object]],
    pareto_summary: dict[str, float],
    outdir: Path,
) -> None:
    metrics_df = pd.DataFrame(metric_rows)
    error_by_cell = (
        pred.groupby("cell_type")
        .agg(
            rows=("sample_id", "count"),
            median_delay_mape=("pct_err_delay_avg_ns", "median"),
            median_power_mape=("pct_err_power_avg_uW", "median"),
            max_delay_abs_err_ns=("abs_err_delay_avg_ns", "max"),
            max_power_abs_err_uW=("abs_err_power_avg_uW", "max"),
        )
        .reset_index()
    )
    selected_cols = [
        "sample_id",
        "cell_type",
        "corner",
        "delay_avg_ns",
        "power_avg_uW",
        "pred_delay_avg_ns",
        "pred_power_avg_uW",
        "pred_composite_score",
        "actual_composite_score",
        "actual_composite_rank",
        "actual_pareto_member",
        "actual_top10pct_member",
        "actual_top20pct_member",
    ]
    lines = [
        "# Primary-Dataset Diagnostics and SPICE-Verified Case Study",
        "",
        "## Held-Out Metrics",
        "",
        markdown_table(metrics_df),
        "",
        "## Error by Cell Type",
        "",
        markdown_table(error_by_cell),
        "",
        "## Pareto Case Study Summary",
        "",
        markdown_table(pd.DataFrame([pareto_summary])),
        "",
        "## Surrogate-Selected Candidates",
        "",
        markdown_table(selected[selected_cols]),
        "",
        "## Output Files",
        "",
        "- `v2_predictions_holdout.csv`",
        "- `v2_pareto_selected_candidates.csv`",
        "- `v2_predicted_vs_spice.png` / `.pdf`",
        "- `v2_error_by_cell.png` / `.pdf`",
        "- `v2_spice_verified_pareto_case.png` / `.pdf`",
    ]
    (outdir / "v2_diagnostics_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    metrics_df.to_csv(outdir / "v2_holdout_metrics.csv", index=False)
    error_by_cell.to_csv(outdir / "v2_error_by_cell.csv", index=False)
    selected.to_csv(outdir / "v2_pareto_selected_candidates.csv", index=False)
    pred.to_csv(outdir / "v2_predictions_holdout.csv", index=False)
    (outdir / "v2_diagnostics_summary.json").write_text(
        json.dumps(
            {
                "metrics": metrics_df.to_dict(orient="records"),
                "pareto_summary": pareto_summary,
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
    train, test = train_test_split(
        df,
        test_size=args.test_size,
        random_state=args.random_state,
        stratify=df["cell_type"],
    )
    pred, _ = fit_models(train, test, args.random_state)

    metric_rows: list[dict[str, object]] = []
    for target in TARGETS:
        row: dict[str, object] = {"target": target, "model": "GradientBoosting", "test_rows": len(test)}
        row.update(metrics(pred[target].to_numpy(), pred[f"pred_{target}"].to_numpy()))
        metric_rows.append(row)

    selected, pareto_summary = pareto_case_study(pred)
    plot_predicted_vs_spice(pred, args.outdir)
    plot_error_by_cell(pred, args.outdir)
    plot_pareto(pred, selected, args.outdir)
    write_report(pred, selected, metric_rows, pareto_summary, args.outdir)

    print(f"Rows used: {len(df)}")
    print(f"Held-out rows: {len(test)}")
    print(f"Wrote {args.outdir / 'v2_diagnostics_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
