#!/usr/bin/env python3
"""
Pool-based active-learning simulation for the primary GF180MCU SPICE dataset.

The script treats the existing SPICE rows as an oracle-backed pool and compares
random sampling against uncertainty-guided sample acquisition. It does not claim
new SPICE simulations; it estimates how many SPICE labels could be saved if the
next simulation point were selected adaptively.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import warnings

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = PROJECT_ROOT / "data" / "dataset_v2_spice_320.csv"
DEFAULT_OUTDIR = PROJECT_ROOT / "results" / "v2_active_learning"
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
    parser = argparse.ArgumentParser(description="Run primary-dataset active-learning sample-efficiency study.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--seeds", nargs="*", type=int, default=[0, 1, 2, 3, 4])
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--initial-per-cell", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--max-labels", type=int, default=200)
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
    rf = RandomForestRegressor(
        n_estimators=120,
        min_samples_leaf=2,
        random_state=random_state,
        n_jobs=-1,
    )
    return Pipeline([("pre", preprocessor()), ("model", rf)])


def metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2 = float(r2_score(y_true, y_pred))
    denom = np.maximum(np.abs(y_true), 1e-12)
    mape = float(np.mean(np.abs((y_true - y_pred) / denom)) * 100)
    return {"r2": r2, "mae": mae, "rmse": rmse, "mape_pct": mape}


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


def initial_indices(train: pd.DataFrame, per_cell: int, seed: int) -> list[int]:
    indices: list[int] = []
    for _, group in train.groupby("cell_type"):
        indices.extend(group.sample(n=min(per_cell, len(group)), random_state=seed).index.tolist())
    return sorted(indices)


def rf_uncertainty(pipe: Pipeline, pool: pd.DataFrame) -> np.ndarray:
    x_pool = pipe.named_steps["pre"].transform(pool[NUMERIC_FEATURES + CATEGORICAL_FEATURES])
    rf = pipe.named_steps["model"]
    tree_preds = np.vstack([tree.predict(x_pool) for tree in rf.estimators_])
    return tree_preds.std(axis=0)


def acquire_random(pool_idx: list[int], batch_size: int, rng: np.random.Generator) -> list[int]:
    n = min(batch_size, len(pool_idx))
    return rng.choice(pool_idx, size=n, replace=False).tolist()


def acquire_uncertainty(pipe: Pipeline, train: pd.DataFrame, pool_idx: list[int], batch_size: int) -> list[int]:
    pool = train.loc[pool_idx]
    uncertainty = rf_uncertainty(pipe, pool)
    order = np.argsort(-uncertainty)
    n = min(batch_size, len(pool_idx))
    return [pool_idx[i] for i in order[:n]]


def run_one(
    train: pd.DataFrame,
    test: pd.DataFrame,
    target: str,
    strategy: str,
    seed: int,
    initial_per_cell: int,
    batch_size: int,
    max_labels: int,
) -> list[dict[str, object]]:
    rng = np.random.default_rng(seed + 2026)
    labeled_idx = initial_indices(train, initial_per_cell, seed)
    pool_idx = sorted(set(train.index.tolist()) - set(labeled_idx))
    rows: list[dict[str, object]] = []

    while True:
        pipe = model(seed)
        labeled = train.loc[labeled_idx]
        pipe.fit(labeled[NUMERIC_FEATURES + CATEGORICAL_FEATURES], labeled[target])
        pred = pipe.predict(test[NUMERIC_FEATURES + CATEGORICAL_FEATURES])
        row: dict[str, object] = {
            "target": target,
            "strategy": strategy,
            "seed": seed,
            "labeled_rows": len(labeled_idx),
            "test_rows": len(test),
        }
        row.update(metrics(test[target].to_numpy(), pred))
        rows.append(row)

        if len(labeled_idx) >= max_labels or not pool_idx:
            break
        if strategy == "random":
            new_idx = acquire_random(pool_idx, batch_size, rng)
        elif strategy == "uncertainty":
            new_idx = acquire_uncertainty(pipe, train, pool_idx, batch_size)
        elif strategy == "hybrid_random_then_uncertainty":
            if len(labeled_idx) < 80:
                new_idx = acquire_random(pool_idx, batch_size, rng)
            else:
                new_idx = acquire_uncertainty(pipe, train, pool_idx, batch_size)
        else:
            raise ValueError(f"Unsupported acquisition strategy: {strategy}")
        labeled_idx = sorted(labeled_idx + new_idx)
        pool_idx = sorted(set(pool_idx) - set(new_idx))
    return rows


def run_experiment(df: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for seed in args.seeds:
        train, test = train_test_split(
            df,
            test_size=args.test_size,
            random_state=seed,
            stratify=df["cell_type"],
        )
        train = train.reset_index(drop=True)
        test = test.reset_index(drop=True)
        for target in TARGETS:
            for strategy in ["random", "uncertainty", "hybrid_random_then_uncertainty"]:
                rows.extend(
                    run_one(
                        train=train,
                        test=test,
                        target=target,
                        strategy=strategy,
                        seed=seed,
                        initial_per_cell=args.initial_per_cell,
                        batch_size=args.batch_size,
                        max_labels=args.max_labels,
                    )
                )
    return pd.DataFrame(rows)


def summarize(results: pd.DataFrame) -> pd.DataFrame:
    return (
        results.groupby(["target", "strategy", "labeled_rows"])
        .agg(
            runs=("r2", "count"),
            median_r2=("r2", "median"),
            min_r2=("r2", "min"),
            median_mae=("mae", "median"),
            median_mape_pct=("mape_pct", "median"),
        )
        .reset_index()
        .sort_values(["target", "strategy", "labeled_rows"])
    )


def best_budget_summary(summary: pd.DataFrame) -> pd.DataFrame:
    pivot = summary.pivot_table(
        index=["target", "labeled_rows"],
        columns="strategy",
        values=["median_r2", "median_mae"],
    )
    pivot.columns = [f"{metric}_{strategy}" for metric, strategy in pivot.columns]
    pivot = pivot.reset_index()
    for strategy in ["uncertainty", "hybrid_random_then_uncertainty"]:
        if {f"median_r2_{strategy}", "median_r2_random"} <= set(pivot.columns):
            pivot[f"median_r2_gain_{strategy}"] = (
                pivot[f"median_r2_{strategy}"] - pivot["median_r2_random"]
            )
        if {f"median_mae_{strategy}", "median_mae_random"} <= set(pivot.columns):
            pivot[f"median_mae_reduction_{strategy}"] = (
                pivot["median_mae_random"] - pivot[f"median_mae_{strategy}"]
            )
    return pivot


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


def plot(summary: pd.DataFrame, outdir: Path) -> None:
    Path("/private/tmp/matplotlib-cache").mkdir(parents=True, exist_ok=True)
    Path("/private/tmp/fontconfig-cache").mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/matplotlib-cache")
    os.environ.setdefault("XDG_CACHE_HOME", "/private/tmp/fontconfig-cache")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = {"delay_avg_ns": "Average delay", "power_avg_uW": "Average power"}
    colors = {
        "random": "#d62728",
        "uncertainty": "#1f77b4",
        "hybrid_random_then_uncertainty": "#2ca02c",
    }
    markers = {"random": "s", "uncertainty": "o", "hybrid_random_then_uncertainty": "^"}
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharex=True)

    for col, target in enumerate(TARGETS):
        target_df = summary[summary["target"] == target]
        for strategy, strategy_df in target_df.groupby("strategy"):
            strategy_df = strategy_df.sort_values("labeled_rows")
            axes[0, col].plot(
                strategy_df["labeled_rows"],
                strategy_df["median_r2"],
                marker=markers[strategy],
                color=colors[strategy],
                linewidth=2,
                label=strategy,
            )
            axes[1, col].plot(
                strategy_df["labeled_rows"],
                strategy_df["median_mae"],
                marker=markers[strategy],
                color=colors[strategy],
                linewidth=2,
                label=strategy,
            )
        axes[0, col].set_title(labels[target])
        axes[0, col].set_ylabel(r"Median $R^2$")
        axes[1, col].set_ylabel("Median MAE")
        axes[1, col].set_xlabel("Labeled primary SPICE dataset rows")
        axes[0, col].grid(True, alpha=0.25)
        axes[1, col].grid(True, alpha=0.25)

    axes[0, 0].legend(frameon=False, loc="lower right")
    fig.suptitle("Pool-based active learning on primary SPICE dataset rows")
    fig.tight_layout()
    fig.savefig(outdir / "v2_active_learning_curves.png", dpi=300, bbox_inches="tight")
    fig.savefig(outdir / "v2_active_learning_curves.pdf", bbox_inches="tight")


def write_report(df: pd.DataFrame, results: pd.DataFrame, outdir: Path) -> None:
    summary = summarize(results)
    budget = best_budget_summary(summary)
    summary.to_csv(outdir / "v2_active_learning_summary.csv", index=False)
    budget.to_csv(outdir / "v2_active_learning_budget_comparison.csv", index=False)
    plot(summary, outdir)

    compact_budget = budget[budget["labeled_rows"].isin([20, 40, 80, 120, 160, 200])].copy()
    lines = [
        "# Primary-Dataset Active-Learning Sample-Efficiency Report",
        "",
        "## Dataset and Protocol",
        "",
        f"- Rows used: {len(df)} publication-eligible GF180MCU/ngspice rows.",
        "- Evaluation protocol: stratified train/test split, then pool-based acquisition from the training pool.",
        "- Initial labeled set: 5 rows per cell, 20 rows total.",
        "- Batch size: 20 rows.",
        "- Model: RandomForestRegressor; uncertainty is the standard deviation across trees.",
        "- Strategies: random sampling, uncertainty-guided acquisition, and a hybrid strategy that uses random sampling until 80 labels and uncertainty afterward.",
        "",
        "## Budget Comparison",
        "",
        markdown_table(compact_budget),
        "",
        "## Output Files",
        "",
        "- `v2_active_learning_results.csv`",
        "- `v2_active_learning_summary.csv`",
        "- `v2_active_learning_budget_comparison.csv`",
        "- `v2_active_learning_curves.png`",
        "- `v2_active_learning_curves.pdf`",
    ]
    (outdir / "v2_active_learning_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (outdir / "v2_active_learning_summary.json").write_text(
        json.dumps(
            {
                "rows_used": int(len(df)),
                "targets": TARGETS,
                "strategies": ["random", "uncertainty", "hybrid_random_then_uncertainty"],
                "budget_comparison": budget.to_dict(orient="records"),
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
    results = run_experiment(df, args)
    results_path = args.outdir / "v2_active_learning_results.csv"
    results.to_csv(results_path, index=False)
    write_report(df, results, args.outdir)

    print(f"Rows used: {len(df)}")
    print(f"Wrote {results_path}")
    print(f"Wrote {args.outdir / 'v2_active_learning_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
