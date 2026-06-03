#!/usr/bin/env python3
"""
Source-aware and weighting ablations for the Microelectronics Journal extension.

This experiment is intentionally conservative. The old 155-row inverter dataset is
treated as auxiliary low-fidelity/model-generated data, while the V2 GF180MCU
ngspice inverter rows are treated as high-fidelity publication data.
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HF_DATASET = PROJECT_ROOT / "data" / "dataset_v2_spice_320.csv"
DEFAULT_LF_DATASET = PROJECT_ROOT / "previous_work" / "legacy_data_and_scripts" / "dataset_hybrid_combined.csv"
DEFAULT_OUTDIR = PROJECT_ROOT / "results" / "source_aware"

COMMON_FEATURES = ["Wn_um", "Vdd", "Temp"]
TARGETS = ["delay_ns", "power_uW"]
WEIGHT_SWEEP = [1.0, 1.5, 2.0, 3.0, 5.0, 10.0]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run source-aware fusion ablations.")
    parser.add_argument("--hf-dataset", type=Path, default=DEFAULT_HF_DATASET)
    parser.add_argument("--lf-dataset", type=Path, default=DEFAULT_LF_DATASET)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--test-size", type=float, default=0.3)
    parser.add_argument("--seeds", nargs="*", type=int, default=list(range(10)))
    return parser.parse_args()


def one_hot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def build_pipeline(include_source: bool, model_name: str, seed: int) -> Pipeline:
    categorical = ["source_label"] if include_source else []
    pre = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), COMMON_FEATURES),
            ("cat", one_hot_encoder(), categorical),
        ],
        remainder="drop",
    )
    if model_name == "GradientBoosting":
        model = GradientBoostingRegressor(random_state=seed)
    elif model_name == "RandomForest":
        model = RandomForestRegressor(
            n_estimators=250,
            min_samples_leaf=2,
            random_state=seed,
            n_jobs=-1,
        )
    else:
        raise ValueError(f"Unsupported model: {model_name}")
    return Pipeline([("pre", pre), ("model", model)])


def metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    mae = mean_absolute_error(y_true, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2 = float(r2_score(y_true, y_pred))
    denom = np.maximum(np.abs(y_true), 1e-12)
    mape = float(np.mean(np.abs((y_true - y_pred) / denom)) * 100)
    return {"r2": r2, "mae": float(mae), "rmse": rmse, "mape_pct": mape}


def load_high_fidelity(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = set(COMMON_FEATURES + ["cell_type", "status", "fidelity", "delay_avg_ns", "power_avg_uW"])
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"High-fidelity dataset is missing columns: {missing}")

    df = df[
        (df["cell_type"] == "INV")
        & (df["status"] == "ok")
        & (df["fidelity"] == "SPICE_GF180MCU")
    ].copy()
    if df.empty:
        raise ValueError("No high-fidelity INV rows found.")
    df["delay_ns"] = df["delay_avg_ns"]
    df["power_uW"] = df["power_avg_uW"]
    df["source_label"] = "HF_SPICE_GF180MCU"
    return df[COMMON_FEATURES + TARGETS + ["source_label"]].reset_index(drop=True)


def load_low_fidelity(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = set(COMMON_FEATURES + ["Power", "Delay", "cell_type", "data_source"])
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Low-fidelity dataset is missing columns: {missing}")

    df = df[df["cell_type"].str.lower() == "inverter"].copy()
    if df.empty:
        raise ValueError("No low-fidelity inverter rows found.")
    df["delay_ns"] = df["Delay"]
    df["power_uW"] = df["Power"]
    df["source_label"] = "LF_LEGACY_MODEL_GENERATED"
    return df[COMMON_FEATURES + TARGETS + ["source_label"]].reset_index(drop=True)


def fit_predict(
    train: pd.DataFrame,
    test: pd.DataFrame,
    target: str,
    include_source: bool,
    model_name: str,
    seed: int,
    sample_weight: np.ndarray | None = None,
) -> np.ndarray:
    pipe = build_pipeline(include_source, model_name, seed)
    features = COMMON_FEATURES + (["source_label"] if include_source else [])
    fit_kwargs = {}
    if sample_weight is not None:
        fit_kwargs["model__sample_weight"] = sample_weight
    pipe.fit(train[features], train[target], **fit_kwargs)
    return pipe.predict(test[features])


def run_protocol(
    name: str,
    train: pd.DataFrame,
    test: pd.DataFrame,
    target: str,
    seed: int,
    model_name: str,
    include_source: bool = False,
    hf_weight: float | None = None,
) -> dict[str, object]:
    weights = None
    if hf_weight is not None:
        weights = np.where(train["source_label"].str.startswith("HF_"), hf_weight, 1.0)
    pred = fit_predict(
        train=train,
        test=test,
        target=target,
        include_source=include_source,
        model_name=model_name,
        seed=seed,
        sample_weight=weights,
    )
    row: dict[str, object] = {
        "protocol": name,
        "selected_protocol": "",
        "target": target,
        "model": model_name,
        "seed": seed,
        "train_hf_rows": int(train["source_label"].str.startswith("HF_").sum()),
        "train_lf_rows": int(train["source_label"].str.startswith("LF_").sum()),
        "test_hf_rows": len(test),
        "include_source": include_source,
        "hf_weight": "" if hf_weight is None else hf_weight,
    }
    row.update(metrics(test[target].to_numpy(), pred))
    return row


def run_residual_correction(
    lf: pd.DataFrame,
    hf_train: pd.DataFrame,
    hf_test: pd.DataFrame,
    target: str,
    seed: int,
    model_name: str,
) -> dict[str, object]:
    lf_base = build_pipeline(include_source=False, model_name=model_name, seed=seed)
    lf_base.fit(lf[COMMON_FEATURES], lf[target])

    train_base = lf_base.predict(hf_train[COMMON_FEATURES])
    test_base = lf_base.predict(hf_test[COMMON_FEATURES])

    residual_train = hf_train.copy()
    residual_train[target] = hf_train[target].to_numpy() - train_base

    residual_model = build_pipeline(include_source=False, model_name=model_name, seed=seed + 1000)
    residual_model.fit(residual_train[COMMON_FEATURES], residual_train[target])
    pred = test_base + residual_model.predict(hf_test[COMMON_FEATURES])

    row: dict[str, object] = {
        "protocol": "two_stage_lf_plus_hf_residual",
        "selected_protocol": "",
        "target": target,
        "model": model_name,
        "seed": seed,
        "train_hf_rows": len(hf_train),
        "train_lf_rows": len(lf),
        "test_hf_rows": len(hf_test),
        "include_source": False,
        "hf_weight": "",
    }
    row.update(metrics(hf_test[target].to_numpy(), pred))
    return row


def candidate_train_frame(name: str, hf_part: pd.DataFrame, lf: pd.DataFrame) -> pd.DataFrame:
    if name == "hf_only":
        return hf_part.copy()
    if name in {
        "naive_merge_equal_weight",
        "weighted_merge_no_source_1.5",
        "weighted_merge_no_source_3.0",
        "source_indicator_equal_weight",
        "source_indicator_weighted_1.5",
    }:
        return pd.concat([hf_part, lf], ignore_index=True)
    raise ValueError(f"Unknown gated candidate: {name}")


def candidate_settings(name: str) -> tuple[bool, float | None]:
    if name == "source_indicator_equal_weight":
        return True, None
    if name == "source_indicator_weighted_1.5":
        return True, 1.5
    if name == "weighted_merge_no_source_1.5":
        return False, 1.5
    if name == "weighted_merge_no_source_3.0":
        return False, 3.0
    return False, None


def run_source_aware_validation_gate(
    lf: pd.DataFrame,
    hf_train_full: pd.DataFrame,
    hf_test: pd.DataFrame,
    target: str,
    seed: int,
    model_name: str,
) -> dict[str, object]:
    tune_train, tune_val = train_test_split(
        hf_train_full,
        test_size=0.25,
        random_state=seed + 2026,
    )
    candidates = [
        "hf_only",
        "naive_merge_equal_weight",
        "weighted_merge_no_source_1.5",
        "weighted_merge_no_source_3.0",
        "source_indicator_equal_weight",
        "source_indicator_weighted_1.5",
    ]
    scored: list[tuple[float, str]] = []

    for candidate in candidates:
        include_source, hf_weight = candidate_settings(candidate)
        train = candidate_train_frame(candidate, tune_train, lf)
        val = tune_val.copy()
        val["source_label"] = "HF_SPICE_GF180MCU"
        weights = None
        if hf_weight is not None:
            weights = np.where(train["source_label"].str.startswith("HF_"), hf_weight, 1.0)
        pred = fit_predict(
            train=train,
            test=val,
            target=target,
            include_source=include_source,
            model_name=model_name,
            seed=seed,
            sample_weight=weights,
        )
        scored.append((r2_score(val[target].to_numpy(), pred), candidate))

    _, selected = max(scored, key=lambda item: item[0])
    include_source, hf_weight = candidate_settings(selected)
    final_train = candidate_train_frame(selected, hf_train_full, lf)
    final_test = hf_test.copy()
    final_test["source_label"] = "HF_SPICE_GF180MCU"
    weights = None
    if hf_weight is not None:
        weights = np.where(final_train["source_label"].str.startswith("HF_"), hf_weight, 1.0)
    pred = fit_predict(
        train=final_train,
        test=final_test,
        target=target,
        include_source=include_source,
        model_name=model_name,
        seed=seed,
        sample_weight=weights,
    )
    row: dict[str, object] = {
        "protocol": "source_aware_validation_gate",
        "selected_protocol": selected,
        "target": target,
        "model": model_name,
        "seed": seed,
        "train_hf_rows": int(final_train["source_label"].str.startswith("HF_").sum()),
        "train_lf_rows": int(final_train["source_label"].str.startswith("LF_").sum()),
        "test_hf_rows": len(hf_test),
        "include_source": include_source,
        "hf_weight": "" if hf_weight is None else hf_weight,
    }
    row.update(metrics(hf_test[target].to_numpy(), pred))
    return row


def run_experiments(hf: pd.DataFrame, lf: pd.DataFrame, seeds: list[int], test_size: float) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    model_names = ["GradientBoosting", "RandomForest"]

    for seed in seeds:
        hf_train, hf_test = train_test_split(hf, test_size=test_size, random_state=seed)
        merged_train = pd.concat([hf_train, lf], ignore_index=True)
        hf_test_for_source = hf_test.copy()
        hf_test_for_source["source_label"] = "HF_SPICE_GF180MCU"

        for target in TARGETS:
            for model_name in model_names:
                rows.append(
                    run_protocol(
                        name="hf_only",
                        train=hf_train,
                        test=hf_test,
                        target=target,
                        seed=seed,
                        model_name=model_name,
                    )
                )
                rows.append(
                    run_protocol(
                        name="lf_only",
                        train=lf,
                        test=hf_test,
                        target=target,
                        seed=seed,
                        model_name=model_name,
                    )
                )
                rows.append(
                    run_protocol(
                        name="naive_merge_equal_weight",
                        train=merged_train,
                        test=hf_test,
                        target=target,
                        seed=seed,
                        model_name=model_name,
                    )
                )
                for weight in WEIGHT_SWEEP:
                    rows.append(
                        run_protocol(
                            name="weighted_merge_no_source",
                            train=merged_train,
                            test=hf_test,
                            target=target,
                            seed=seed,
                            model_name=model_name,
                            hf_weight=weight,
                        )
                    )
                rows.append(
                    run_protocol(
                        name="source_indicator_equal_weight",
                        train=merged_train,
                        test=hf_test_for_source,
                        target=target,
                        seed=seed,
                        model_name=model_name,
                        include_source=True,
                    )
                )
                for weight in [1.5, 3.0]:
                    rows.append(
                        run_protocol(
                            name="source_indicator_weighted",
                            train=merged_train,
                            test=hf_test_for_source,
                            target=target,
                            seed=seed,
                            model_name=model_name,
                            include_source=True,
                            hf_weight=weight,
                        )
                    )
                rows.append(run_residual_correction(lf, hf_train, hf_test, target, seed, model_name))
                rows.append(run_source_aware_validation_gate(lf, hf_train, hf_test, target, seed, model_name))
    return pd.DataFrame(rows)


def summarize(results: pd.DataFrame) -> pd.DataFrame:
    grouped = results.copy()
    grouped["hf_weight_group"] = grouped["hf_weight"].fillna("").astype(str)
    grouped.loc[grouped["protocol"] == "source_aware_validation_gate", "hf_weight_group"] = "selected"
    summary = (
        grouped.groupby(["target", "model", "protocol", "hf_weight_group"], dropna=False)
        .agg(
            runs=("r2", "count"),
            median_r2=("r2", "median"),
            mean_r2=("r2", "mean"),
            median_mae=("mae", "median"),
            median_rmse=("rmse", "median"),
            median_mape_pct=("mape_pct", "median"),
        )
        .reset_index()
        .sort_values(["target", "model", "median_r2"], ascending=[True, True, False])
    )
    return summary.rename(columns={"hf_weight_group": "hf_weight"})


def best_by_target_model(summary: pd.DataFrame) -> pd.DataFrame:
    return (
        summary.sort_values(["target", "model", "median_r2"], ascending=[True, True, False])
        .groupby(["target", "model"])
        .head(1)
        .reset_index(drop=True)
    )


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
    hf: pd.DataFrame,
    lf: pd.DataFrame,
    results: pd.DataFrame,
    outdir: Path,
    lf_dataset: Path,
) -> None:
    summary = summarize(results)
    best = best_by_target_model(summary)
    gb = summary[summary["model"] == "GradientBoosting"].copy()
    gb_core = gb[
        gb["protocol"].isin(
            [
                "hf_only",
                "lf_only",
                "naive_merge_equal_weight",
                "weighted_merge_no_source",
                "source_indicator_equal_weight",
                "source_indicator_weighted",
                "two_stage_lf_plus_hf_residual",
                "source_aware_validation_gate",
            ]
        )
    ]
    weight_sweep = gb[
        (gb["protocol"] == "weighted_merge_no_source")
        & (gb["target"].isin(TARGETS))
    ][["target", "hf_weight", "median_r2", "median_mae", "median_mape_pct"]]
    gate_selection = (
        results[results["protocol"] == "source_aware_validation_gate"]
        .groupby(["target", "model", "selected_protocol"])
        .size()
        .reset_index(name="count")
        .sort_values(["target", "model", "count"], ascending=[True, True, False])
    )
    try:
        lf_dataset_label = lf_dataset.relative_to(PROJECT_ROOT)
    except ValueError:
        lf_dataset_label = lf_dataset

    lines = [
        "# Source-Aware Fusion Ablation Report",
        "",
        "## Dataset",
        "",
        f"- High-fidelity target data: {len(hf)} V2 `INV` rows from GF180MCU/ngspice.",
        f"- Low-fidelity auxiliary data: {len(lf)} legacy inverter rows from `{lf_dataset_label}`.",
        "- Shared feature space for this ablation: `Wn_um`, `Vdd`, and `Temp`.",
        "- Evaluation data: held-out high-fidelity V2 `INV` rows only.",
        "",
        "## Best Protocols by Target and Model",
        "",
        markdown_table(
            best[
                [
                    "target",
                    "model",
                    "protocol",
                    "hf_weight",
                    "median_r2",
                    "median_mae",
                    "median_mape_pct",
                ]
            ]
        ),
        "",
        "## GradientBoosting Protocol Summary",
        "",
        markdown_table(
            gb_core[
                [
                    "target",
                    "protocol",
                    "hf_weight",
                    "median_r2",
                    "median_mae",
                    "median_mape_pct",
                ]
            ]
        ),
        "",
        "## GradientBoosting Weight Sweep Without Source Indicator",
        "",
        markdown_table(weight_sweep),
        "",
        "## Source-Aware Validation Gate Selections",
        "",
        markdown_table(gate_selection),
        "",
        "## Interpretation Notes",
        "",
        "- `lf_only` measures how poorly the legacy source transfers when used as if it were SPICE-equivalent.",
        "- `naive_merge_equal_weight` tests the unsafe merge strategy from the preliminary manuscript.",
        "- `weighted_merge_no_source` tests whether a fixed high-fidelity weight such as 1.5x is justified.",
        "- `source_indicator_*` lets the regressor distinguish high- and low-fidelity rows.",
        "- `two_stage_lf_plus_hf_residual` uses the low-fidelity model as a base trend and learns a high-fidelity residual.",
        "- `source_aware_validation_gate` chooses whether to use the auxiliary source based on a held-out high-fidelity validation subset, preventing blind negative transfer.",
    ]
    (outdir / "source_aware_ablation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary.to_csv(outdir / "source_aware_ablation_summary.csv", index=False)
    (outdir / "source_aware_ablation_summary.json").write_text(
        json.dumps(
            {
                "hf_rows": int(len(hf)),
                "lf_rows": int(len(lf)),
                "features": COMMON_FEATURES,
                "targets": TARGETS,
                "best": best.to_dict(orient="records"),
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

    hf = load_high_fidelity(args.hf_dataset)
    lf = load_low_fidelity(args.lf_dataset)
    results = run_experiments(hf, lf, args.seeds, args.test_size)
    results_path = args.outdir / "source_aware_ablation_results.csv"
    results.to_csv(results_path, index=False)
    write_report(hf, lf, results, args.outdir, args.lf_dataset)

    print(f"High-fidelity INV rows: {len(hf)}")
    print(f"Low-fidelity legacy rows: {len(lf)}")
    print(f"Wrote {results_path}")
    print(f"Wrote {args.outdir / 'source_aware_ablation_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
