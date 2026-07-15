#!/usr/bin/env python3
"""Run genuine simulator-in-the-loop support acquisition for unseen corners.

The experiment uses the primary V2 rows from two process corners as the base
training set. Candidate points in a new V4 pool contain features only. At each
round, an acquisition strategy selects a batch, the script writes the selected
netlists, launches ngspice, parses the measured labels, and retrains the
surrogate. The independent V3 target-corner rows are used only for evaluation;
their labels are never passed to an acquisition function.

Five strategies are compared on identical candidate pools:

* random
* cell_balanced_random
* space_filling
* uncertainty
* cell_balanced_space_filling

The final strategy selects one point per cell in each four-query batch and
maximizes feature-space distance from previously queried target-corner points.
Its pure-diversity form was locked by a V2-only development study before the
independent V4/V3 experiment.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
import json
import math
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace
from typing import Any
import warnings

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, spearmanr, wilcoxon
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    ndcg_score,
    r2_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from spice_v2.generate_spice_dataset import (  # noqa: E402
    DEFAULT_PDK_ROOT,
    Sample,
    find_model_file,
    input_arc,
    lhs_samples,
    result_row,
    run_ngspice,
    write_netlist,
)


DEFAULT_PRIMARY = PROJECT_ROOT / "data" / "dataset_v2_spice_320.csv"
DEFAULT_VALIDATION = PROJECT_ROOT / "data" / "dataset_v3_spice_480.csv"
DEFAULT_OUTDIR = PROJECT_ROOT / "results" / "online_spice_corner_calibration"

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
CELLS = ["INV", "NAND2", "NOR2", "XOR2"]
CORNERS = ["ff", "ss", "typical"]
STRATEGIES = [
    "random",
    "cell_balanced_random",
    "space_filling",
    "uncertainty",
    "cell_balanced_space_filling",
]
PROPOSED_STRATEGY = "cell_balanced_space_filling"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run simulator-in-the-loop same-corner support acquisition."
    )
    parser.add_argument("--primary-dataset", type=Path, default=DEFAULT_PRIMARY)
    parser.add_argument("--validation-dataset", type=Path, default=DEFAULT_VALIDATION)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--pdk-root", type=Path, default=DEFAULT_PDK_ROOT)
    parser.add_argument("--model-file", type=Path, default=None)
    parser.add_argument("--nmos-model", default="nmos_3p3")
    parser.add_argument("--pmos-model", default="pmos_3p3")
    parser.add_argument("--seeds", nargs="*", type=int, default=[0, 1, 2])
    parser.add_argument("--heldout-corners", nargs="*", default=CORNERS)
    parser.add_argument("--strategies", nargs="*", default=STRATEGIES)
    parser.add_argument("--candidate-per-cell", type=int, default=24)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--max-support", type=int, default=48)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--n-estimators", type=int, default=240)
    parser.add_argument("--uncertainty-weight", type=float, default=0.00)
    parser.add_argument("--diversity-weight", type=float, default=1.00)
    parser.add_argument("--delay-r2-threshold", type=float, default=0.75)
    parser.add_argument("--ranking-recall-threshold", type=float, default=0.90)
    parser.add_argument("--top-fraction", type=float, default=0.20)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--summarize-only", action="store_true")
    args = parser.parse_args()

    invalid_corners = sorted(set(args.heldout_corners) - set(CORNERS))
    invalid_strategies = sorted(set(args.strategies) - set(STRATEGIES))
    if invalid_corners:
        parser.error(f"Unsupported corners: {invalid_corners}")
    if invalid_strategies:
        parser.error(f"Unsupported strategies: {invalid_strategies}")
    if args.batch_size <= 0 or args.max_support <= 0:
        parser.error("batch-size and max-support must be positive")
    if args.candidate_per_cell * len(CELLS) < args.max_support:
        parser.error("candidate pool must contain at least max-support points")
    if not math.isclose(args.uncertainty_weight + args.diversity_weight, 1.0, abs_tol=1e-9):
        parser.error("uncertainty-weight and diversity-weight must sum to 1")
    for attribute in ["primary_dataset", "validation_dataset", "outdir", "pdk_root"]:
        path = Path(getattr(args, attribute)).expanduser()
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        setattr(args, attribute, path.resolve())
    if args.model_file is not None:
        model_file = Path(args.model_file).expanduser()
        if not model_file.is_absolute():
            model_file = PROJECT_ROOT / model_file
        args.model_file = model_file.resolve()
    return args


def one_hot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def build_model(seed: int, n_estimators: int) -> Pipeline:
    pre = ColumnTransformer(
        [
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", one_hot_encoder(), CATEGORICAL_FEATURES),
        ]
    )
    model = ExtraTreesRegressor(
        n_estimators=n_estimators,
        min_samples_leaf=2,
        max_features=1.0,
        random_state=seed,
        n_jobs=-1,
    )
    return Pipeline([("pre", pre), ("model", model)])


def load_spice_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = set(FEATURES + TARGETS + ["status", "fidelity"])
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"{path} is missing required columns: {missing}")
    df = df[(df["status"] == "ok") & (df["fidelity"] == "SPICE_GF180MCU")].copy()
    if df.empty:
        raise ValueError(f"No publication-eligible rows in {path}")
    return df.reset_index(drop=True)


def sample_to_feature_row(sample: Sample, seed: int, heldout_corner: str) -> dict[str, Any]:
    return {
        "candidate_id": sample.sample_id,
        "pool_seed": seed,
        "heldout_corner": heldout_corner,
        "cell_type": sample.cell_type,
        "input_arc": input_arc(sample.cell_type),
        "Wn_um": sample.wn_um,
        "L_um": sample.length_um,
        "Wp_Wn_ratio": sample.wp_wn_ratio,
        "Vdd": sample.vdd,
        "Temp": sample.temp,
        "Cload_fF": sample.cload_ff,
        "slew_ps": sample.slew_ps,
        "corner": heldout_corner,
    }


def candidate_pool(seed: int, heldout_corner: str, candidate_per_cell: int) -> pd.DataFrame:
    corner_index = CORNERS.index(heldout_corner)
    pool_seed = 20260711 + seed * 101 + corner_index * 17
    raw = lhs_samples(CELLS, candidate_per_cell, pool_seed, 0.28, (1.62, 1.98))
    samples = [replace(sample, corner=heldout_corner) for sample in raw]
    rows = [sample_to_feature_row(sample, seed, heldout_corner) for sample in samples]
    pool = pd.DataFrame(rows)
    pool["candidate_id"] = np.arange(len(pool), dtype=int)
    return pool


def row_to_sample(row: pd.Series, sample_id: int) -> Sample:
    return Sample(
        sample_id=sample_id,
        cell_type=str(row["cell_type"]),
        wn_um=float(row["Wn_um"]),
        length_um=float(row["L_um"]),
        wp_wn_ratio=float(row["Wp_Wn_ratio"]),
        vdd=float(row["Vdd"]),
        temp=float(row["Temp"]),
        cload_ff=float(row["Cload_fF"]),
        slew_ps=float(row["slew_ps"]),
        corner=str(row["corner"]),
    )


def fit_models(
    train: pd.DataFrame,
    seed: int,
    n_estimators: int,
) -> dict[str, Pipeline]:
    models: dict[str, Pipeline] = {}
    for target_index, target in enumerate(TARGETS):
        pipe = build_model(seed + target_index * 1009, n_estimators)
        pipe.fit(train[FEATURES], train[target])
        models[target] = pipe
    return models


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "r2": float(r2_score(y_true, y_pred)),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
    }


def normalized_score(delay: np.ndarray, power: np.ndarray) -> np.ndarray:
    def unit(values: np.ndarray) -> np.ndarray:
        span = float(np.max(values) - np.min(values))
        if span <= 1e-15:
            return np.zeros_like(values, dtype=float)
        return (values - np.min(values)) / span

    return 0.5 * unit(np.asarray(delay, dtype=float)) + 0.5 * unit(np.asarray(power, dtype=float))


def finite_stat(result: Any) -> float:
    value = float(result.statistic)
    return value if math.isfinite(value) else float("nan")


def ranking_metrics(
    actual_delay: np.ndarray,
    actual_power: np.ndarray,
    pred_delay: np.ndarray,
    pred_power: np.ndarray,
    top_fraction: float,
) -> dict[str, float]:
    actual = normalized_score(actual_delay, actual_power)
    predicted = normalized_score(pred_delay, pred_power)
    n = len(actual)
    top_k = max(1, int(math.ceil(n * top_fraction)))
    actual_top = set(np.argsort(actual)[:top_k].tolist())
    predicted_top = set(np.argsort(predicted)[:top_k].tolist())
    overlap = len(actual_top & predicted_top)

    actual_relevance = 1.0 - actual
    predicted_relevance = 1.0 - predicted
    return {
        "spearman": finite_stat(spearmanr(predicted, actual)),
        "kendall_tau": finite_stat(kendalltau(predicted, actual)),
        "top20_precision": overlap / top_k,
        "top20_recall": overlap / top_k,
        "ndcg_top20": float(
            ndcg_score(actual_relevance.reshape(1, -1), predicted_relevance.reshape(1, -1), k=top_k)
        ),
    }


def evaluate(
    base_train: pd.DataFrame,
    support: pd.DataFrame,
    validation: pd.DataFrame,
    seed: int,
    n_estimators: int,
    top_fraction: float,
) -> tuple[dict[str, float], dict[str, Pipeline]]:
    train = base_train if support.empty else pd.concat([base_train, support], ignore_index=True)
    models = fit_models(train, seed, n_estimators)
    predictions = {target: models[target].predict(validation[FEATURES]) for target in TARGETS}

    row: dict[str, float] = {}
    for target in TARGETS:
        metrics = regression_metrics(validation[target].to_numpy(), predictions[target])
        prefix = "delay" if target == "delay_avg_ns" else "power"
        row.update({f"{prefix}_{key}": value for key, value in metrics.items()})

    cell_r2: list[float] = []
    for cell in CELLS:
        mask = validation["cell_type"].eq(cell).to_numpy()
        if int(mask.sum()) >= 2:
            value = float(r2_score(validation.loc[mask, "delay_avg_ns"], predictions["delay_avg_ns"][mask]))
            row[f"delay_r2_{cell.lower()}"] = value
            cell_r2.append(value)
    row["worst_cell_delay_r2"] = float(min(cell_r2))
    row.update(
        ranking_metrics(
            validation["delay_avg_ns"].to_numpy(),
            validation["power_avg_uW"].to_numpy(),
            predictions["delay_avg_ns"],
            predictions["power_avg_uW"],
            top_fraction,
        )
    )
    return row, models


def tree_uncertainty(pipe: Pipeline, candidates: pd.DataFrame) -> np.ndarray:
    transformed = pipe.named_steps["pre"].transform(candidates[FEATURES])
    ensemble = pipe.named_steps["model"]
    predictions = np.vstack([tree.predict(transformed) for tree in ensemble.estimators_])
    return predictions.std(axis=0)


def scale01(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    finite = np.isfinite(values)
    if not finite.any():
        return np.zeros_like(values)
    lo = float(np.min(values[finite]))
    hi = float(np.max(values[finite]))
    if hi - lo <= 1e-15:
        return np.zeros_like(values)
    scaled = (values - lo) / (hi - lo)
    scaled[~finite] = 0.0
    return scaled


def geometry_matrix(pool: pd.DataFrame) -> np.ndarray:
    numeric = pool[NUMERIC_FEATURES].to_numpy(dtype=float)
    means = numeric.mean(axis=0)
    scales = numeric.std(axis=0)
    scales[scales <= 1e-15] = 1.0
    numeric = (numeric - means) / scales
    cell_one_hot = pd.get_dummies(pool["cell_type"], dtype=float).reindex(columns=CELLS, fill_value=0).to_numpy()
    return np.hstack([numeric, cell_one_hot])


def min_distances(
    geometry: np.ndarray,
    available_positions: np.ndarray,
    selected_positions: list[int],
) -> np.ndarray:
    available = geometry[available_positions]
    if selected_positions:
        selected = geometry[np.asarray(selected_positions, dtype=int)]
        distances = np.sqrt(((available[:, None, :] - selected[None, :, :]) ** 2).sum(axis=2))
        return distances.min(axis=1)
    centroid = geometry.mean(axis=0)
    return np.sqrt(((available - centroid) ** 2).sum(axis=1))


def balanced_pick(
    available: pd.DataFrame,
    scores: pd.Series,
    batch_size: int,
    rng: np.random.Generator,
    random_within_cell: bool,
) -> list[int]:
    chosen: list[int] = []
    cells = [cell for cell in CELLS if (available["cell_type"] == cell).any()]
    if not cells:
        return chosen

    while len(chosen) < batch_size:
        progress = False
        for cell in cells:
            if len(chosen) >= batch_size:
                break
            cell_ids = available.loc[
                (available["cell_type"] == cell) & (~available["candidate_id"].isin(chosen)),
                "candidate_id",
            ].tolist()
            if not cell_ids:
                continue
            if random_within_cell:
                candidate_id = int(rng.choice(cell_ids))
            else:
                candidate_id = int(scores.loc[cell_ids].idxmax())
            chosen.append(candidate_id)
            progress = True
        if not progress:
            break
    return chosen


def acquire(
    strategy: str,
    pool: pd.DataFrame,
    selected_ids: list[int],
    models: dict[str, Pipeline],
    batch_size: int,
    rng: np.random.Generator,
    uncertainty_weight: float,
    diversity_weight: float,
) -> pd.DataFrame:
    available = pool[~pool["candidate_id"].isin(selected_ids)].copy()
    if available.empty:
        return available
    batch_size = min(batch_size, len(available))
    available = available.set_index("candidate_id", drop=False)

    geometry = geometry_matrix(pool)
    id_to_position = {int(cid): pos for pos, cid in enumerate(pool["candidate_id"].tolist())}
    available_positions = np.asarray([id_to_position[int(cid)] for cid in available.index], dtype=int)
    selected_positions = [id_to_position[int(cid)] for cid in selected_ids]
    diversity_raw = min_distances(geometry, available_positions, selected_positions)
    diversity = pd.Series(scale01(diversity_raw), index=available.index, dtype=float)
    uncertainty_raw = tree_uncertainty(models["delay_avg_ns"], available)
    uncertainty = pd.Series(scale01(uncertainty_raw), index=available.index, dtype=float)

    if strategy == "random":
        chosen = rng.choice(available.index.to_numpy(), size=batch_size, replace=False).astype(int).tolist()
        score = pd.Series(np.nan, index=available.index)
    elif strategy == "cell_balanced_random":
        score = pd.Series(np.nan, index=available.index)
        chosen = balanced_pick(available, score, batch_size, rng, random_within_cell=True)
    elif strategy == "space_filling":
        chosen = []
        remaining = available.copy()
        greedy_selected = selected_positions.copy()
        while len(chosen) < batch_size and not remaining.empty:
            remaining_positions = np.asarray(
                [id_to_position[int(cid)] for cid in remaining.index], dtype=int
            )
            distances = min_distances(geometry, remaining_positions, greedy_selected)
            pick_position = int(np.argmax(distances))
            candidate_id = int(remaining.index[pick_position])
            chosen.append(candidate_id)
            greedy_selected.append(id_to_position[candidate_id])
            remaining = remaining.drop(index=candidate_id)
        score = diversity
    elif strategy == "uncertainty":
        score = uncertainty
        chosen = score.nlargest(batch_size).index.astype(int).tolist()
    elif strategy == PROPOSED_STRATEGY:
        score = uncertainty_weight * uncertainty + diversity_weight * diversity
        chosen = balanced_pick(available, score, batch_size, rng, random_within_cell=False)
    else:
        raise ValueError(f"Unsupported strategy: {strategy}")

    selected = available.loc[chosen].copy()
    selected["acquisition_score"] = score.reindex(chosen).to_numpy()
    selected["delay_uncertainty_scaled"] = uncertainty.reindex(chosen).to_numpy()
    selected["diversity_scaled"] = diversity.reindex(chosen).to_numpy()
    return selected.reset_index(drop=True)


def unique_sample_id(seed: int, corner: str, strategy: str, query_order: int) -> int:
    return (
        4_000_000
        + seed * 100_000
        + CORNERS.index(corner) * 10_000
        + STRATEGIES.index(strategy) * 1_000
        + query_order
    )


def simulate_one(
    candidate: pd.Series,
    query_order: int,
    batch_index: int,
    seed: int,
    heldout_corner: str,
    strategy: str,
    model_file: Path,
    generator_args: SimpleNamespace,
) -> dict[str, Any]:
    sample_id = unique_sample_id(seed, heldout_corner, strategy, query_order)
    sample = row_to_sample(candidate, sample_id)
    started = time.perf_counter()
    netlist_path = write_netlist(sample, model_file, generator_args)
    returncode, measurements, log_path = run_ngspice(
        netlist_path,
        sample,
        model_file,
        generator_args.log_dir,
    )
    wall_time = time.perf_counter() - started
    row = result_row(
        sample,
        netlist_path,
        log_path,
        model_file,
        measurements,
        returncode,
        generator_args,
    )
    row.update(
        {
            "candidate_id": int(candidate["candidate_id"]),
            "seed": seed,
            "pool_seed": seed,
            "heldout_corner": heldout_corner,
            "strategy": strategy,
            "query_order": query_order,
            "batch_index": batch_index,
            "spice_wall_time_s": wall_time,
            "acquisition_score": candidate.get("acquisition_score", np.nan),
            "delay_uncertainty_scaled": candidate.get("delay_uncertainty_scaled", np.nan),
            "diversity_scaled": candidate.get("diversity_scaled", np.nan),
        }
    )
    return row


def simulate_batch(
    selected: pd.DataFrame,
    start_query_order: int,
    batch_index: int,
    seed: int,
    heldout_corner: str,
    strategy: str,
    model_file: Path,
    run_dir: Path,
    args: argparse.Namespace,
) -> pd.DataFrame:
    generator_args = SimpleNamespace(
        netlist_dir=run_dir / "netlists",
        log_dir=run_dir / "logs",
        allow_generic_debug_models=False,
        nmos_model=args.nmos_model,
        pmos_model=args.pmos_model,
        statistical_mode="off",
        seed=seed,
        dry_run=False,
    )
    rows: list[dict[str, Any]] = []
    workers = max(1, min(args.workers, len(selected)))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {}
        for offset, (_, candidate) in enumerate(selected.iterrows(), start=1):
            query_order = start_query_order + offset
            future = executor.submit(
                simulate_one,
                candidate,
                query_order,
                batch_index,
                seed,
                heldout_corner,
                strategy,
                model_file,
                generator_args,
            )
            futures[future] = query_order
        for future in as_completed(futures):
            rows.append(future.result())
    return pd.DataFrame(rows).sort_values("query_order").reset_index(drop=True)


def support_frame(queries: pd.DataFrame) -> pd.DataFrame:
    if queries.empty:
        return pd.DataFrame(columns=FEATURES + TARGETS)
    successful = queries[
        (queries["status"] == "ok")
        & queries["delay_avg_ns"].notna()
        & queries["power_avg_uW"].notna()
    ].copy()
    return successful


def trajectory_row(
    metrics: dict[str, float],
    queries: pd.DataFrame,
    seed: int,
    heldout_corner: str,
    strategy: str,
) -> dict[str, Any]:
    successful = support_frame(queries)
    counts = successful["cell_type"].value_counts().reindex(CELLS, fill_value=0)
    row: dict[str, Any] = {
        "seed": seed,
        "heldout_corner": heldout_corner,
        "strategy": strategy,
        "spice_queries": len(queries),
        "successful_support_rows": len(successful),
        "failed_queries": int(len(queries) - len(successful)),
        "cumulative_spice_wall_time_s": float(queries["spice_wall_time_s"].sum()) if not queries.empty else 0.0,
        "support_balance_range": int(counts.max() - counts.min()) if len(counts) else 0,
    }
    row.update({f"support_{cell.lower()}": int(counts[cell]) for cell in CELLS})
    row.update(metrics)
    return row


def run_directory(outdir: Path, seed: int, corner: str, strategy: str) -> Path:
    return outdir / "runs" / f"seed_{seed}" / f"corner_{corner}" / strategy


def run_one(
    primary: pd.DataFrame,
    validation: pd.DataFrame,
    pool: pd.DataFrame,
    model_file: Path,
    seed: int,
    heldout_corner: str,
    strategy: str,
    args: argparse.Namespace,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    run_dir = run_directory(args.outdir, seed, heldout_corner, strategy)
    run_dir.mkdir(parents=True, exist_ok=True)
    queries_path = run_dir / "queries.csv"
    trajectory_path = run_dir / "trajectory.csv"

    if args.resume and queries_path.exists():
        queries = pd.read_csv(queries_path)
    else:
        queries = pd.DataFrame()
    if not queries.empty and "seed" not in queries.columns:
        queries["seed"] = seed
        queries.to_csv(queries_path, index=False)
    if args.resume and trajectory_path.exists():
        prior_trajectory = pd.read_csv(trajectory_path)
        trajectory_rows: list[dict[str, Any]] = prior_trajectory.to_dict(orient="records")
    else:
        trajectory_rows = []

    base_train = primary[primary["corner"] != heldout_corner].copy().reset_index(drop=True)
    target_validation = validation[validation["corner"] == heldout_corner].copy().reset_index(drop=True)
    if base_train.empty or target_validation.empty:
        raise ValueError(f"Missing base or validation rows for corner {heldout_corner}")

    selected_ids = queries["candidate_id"].astype(int).tolist() if not queries.empty else []
    rng_seed_base = (
        900_000
        + seed * 101
        + CORNERS.index(heldout_corner) * 17
        + STRATEGIES.index(strategy) * 13
    )

    while True:
        support = support_frame(queries)
        metrics, models = evaluate(
            base_train,
            support,
            target_validation,
            seed,
            args.n_estimators,
            args.top_fraction,
        )
        evaluated_budgets = {int(row["spice_queries"]) for row in trajectory_rows}
        if len(queries) not in evaluated_budgets:
            trajectory_rows.append(
                trajectory_row(metrics, queries, seed, heldout_corner, strategy)
            )
        trajectory_rows.sort(key=lambda row: int(row["spice_queries"]))
        pd.DataFrame(trajectory_rows).to_csv(trajectory_path, index=False)

        if len(queries) >= args.max_support or len(selected_ids) >= len(pool):
            break

        rng = np.random.default_rng(rng_seed_base + len(queries) * 1009)
        selected = acquire(
            strategy,
            pool,
            selected_ids,
            models,
            min(args.batch_size, args.max_support - len(queries)),
            rng,
            args.uncertainty_weight,
            args.diversity_weight,
        )
        if selected.empty:
            break
        batch = simulate_batch(
            selected,
            len(queries),
            len(queries) // args.batch_size + 1,
            seed,
            heldout_corner,
            strategy,
            model_file,
            run_dir,
            args,
        )
        queries = pd.concat([queries, batch], ignore_index=True)
        queries.to_csv(queries_path, index=False)
        selected_ids = queries["candidate_id"].astype(int).tolist()
        latest = trajectory_rows[-1]
        print(
            f"seed={seed} corner={heldout_corner} strategy={strategy} "
            f"queries={len(queries)}/{args.max_support} "
            f"previous_delay_r2={latest['delay_r2']:.4f}",
            flush=True,
        )

    return queries, pd.DataFrame(trajectory_rows)


def summarize_trajectory(trajectory: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        "delay_r2",
        "delay_mae",
        "power_r2",
        "power_mae",
        "worst_cell_delay_r2",
        "spearman",
        "top20_recall",
        "ndcg_top20",
        "cumulative_spice_wall_time_s",
        "support_balance_range",
    ]
    aggregations: dict[str, tuple[str, str]] = {"runs": ("seed", "count")}
    for metric in metrics:
        aggregations[f"median_{metric}"] = (metric, "median")
        aggregations[f"q25_{metric}"] = (metric, lambda values: values.quantile(0.25))
        aggregations[f"q75_{metric}"] = (metric, lambda values: values.quantile(0.75))
    return (
        trajectory.groupby(["heldout_corner", "strategy", "spice_queries"])
        .agg(**aggregations)
        .reset_index()
        .sort_values(["heldout_corner", "strategy", "spice_queries"])
    )


def threshold_crossings(trajectory: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (seed, corner, strategy), group in trajectory.groupby(
        ["seed", "heldout_corner", "strategy"]
    ):
        group = group.sort_values("spice_queries")
        definitions = {
            "delay_r2": group["delay_r2"] >= args.delay_r2_threshold,
            "top20_recall": group["top20_recall"] >= args.ranking_recall_threshold,
            "joint": (group["delay_r2"] >= args.delay_r2_threshold)
            & (group["top20_recall"] >= args.ranking_recall_threshold),
        }
        for threshold_name, mask in definitions.items():
            reached = group[mask]
            if reached.empty:
                budget = np.nan
                wall_time = np.nan
            else:
                first = reached.iloc[0]
                budget = float(first["spice_queries"])
                wall_time = float(first["cumulative_spice_wall_time_s"])
            rows.append(
                {
                    "seed": seed,
                    "heldout_corner": corner,
                    "strategy": strategy,
                    "threshold": threshold_name,
                    "reached": not reached.empty,
                    "spice_queries_to_threshold": budget,
                    "spice_wall_time_to_threshold_s": wall_time,
                }
            )
    return pd.DataFrame(rows)


def summarize_thresholds(crossings: pd.DataFrame) -> pd.DataFrame:
    summary = (
        crossings.groupby(["heldout_corner", "strategy", "threshold"])
        .agg(
            runs=("seed", "count"),
            reached_runs=("reached", "sum"),
            median_queries=("spice_queries_to_threshold", "median"),
            median_wall_time_s=("spice_wall_time_to_threshold_s", "median"),
        )
        .reset_index()
    )
    random_budget = summary[summary["strategy"] == "random"][
        ["heldout_corner", "threshold", "runs", "reached_runs", "median_queries"]
    ].rename(
        columns={
            "runs": "random_runs",
            "reached_runs": "random_reached_runs",
            "median_queries": "random_median_queries",
        }
    )
    summary = summary.merge(random_budget, on=["heldout_corner", "threshold"], how="left")
    complete_comparison = (
        (summary["reached_runs"] == summary["runs"])
        & (summary["random_reached_runs"] == summary["random_runs"])
    )
    summary["query_reduction_vs_random_pct"] = np.where(
        complete_comparison & (summary["random_median_queries"] > 0),
        100.0
        * (summary["random_median_queries"] - summary["median_queries"])
        / summary["random_median_queries"],
        np.nan,
    )
    return summary


def holm_adjust(p_values: list[float]) -> list[float]:
    n = len(p_values)
    order = np.argsort(p_values)
    adjusted = np.empty(n, dtype=float)
    running = 0.0
    for rank, index in enumerate(order):
        value = min(1.0, (n - rank) * p_values[index])
        running = max(running, value)
        adjusted[index] = running
    return adjusted.tolist()


def paired_tests(trajectory: pd.DataFrame, budgets: list[int]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    metrics = ["delay_r2", "worst_cell_delay_r2", "top20_recall"]
    for budget in budgets:
        at_budget = trajectory[trajectory["spice_queries"] == budget]
        for metric in metrics:
            pivot = at_budget.pivot_table(
                index=["seed", "heldout_corner"],
                columns="strategy",
                values=metric,
            )
            if PROPOSED_STRATEGY not in pivot:
                continue
            for baseline in [strategy for strategy in STRATEGIES if strategy != PROPOSED_STRATEGY]:
                if baseline not in pivot:
                    continue
                paired = pivot[[PROPOSED_STRATEGY, baseline]].dropna()
                if paired.empty:
                    continue
                difference = paired[PROPOSED_STRATEGY] - paired[baseline]
                if np.allclose(difference.to_numpy(), 0.0):
                    statistic, p_value = 0.0, 1.0
                else:
                    statistic, p_value = wilcoxon(
                        paired[PROPOSED_STRATEGY],
                        paired[baseline],
                        alternative="two-sided",
                        zero_method="wilcox",
                    )
                nonzero = difference[~np.isclose(difference, 0.0)]
                if nonzero.empty:
                    rank_biserial = 0.0
                else:
                    absolute_ranks = pd.Series(
                        pd.Series(nonzero.abs()).rank(method="average").to_numpy(),
                        index=nonzero.index,
                    )
                    positive = float(absolute_ranks[nonzero > 0].sum())
                    negative = float(absolute_ranks[nonzero < 0].sum())
                    rank_biserial = (positive - negative) / (positive + negative)
                rows.append(
                    {
                        "budget": budget,
                        "metric": metric,
                        "baseline": baseline,
                        "pairs": len(paired),
                        "median_proposed": float(paired[PROPOSED_STRATEGY].median()),
                        "median_baseline": float(paired[baseline].median()),
                        "median_difference": float(difference.median()),
                        "matched_rank_biserial": rank_biserial,
                        "wilcoxon_statistic": float(statistic),
                        "p_raw": float(p_value),
                    }
                )
    result = pd.DataFrame(rows)
    if not result.empty:
        result["p_holm"] = np.nan
        for _, family in result.groupby(["budget", "metric"]):
            adjusted = holm_adjust(family["p_raw"].tolist())
            result.loc[family.index, "p_holm"] = adjusted
    return result


def markdown_table(df: pd.DataFrame, digits: int = 4) -> str:
    if df.empty:
        return "No rows."
    rendered = df.copy()
    for column in rendered.columns:
        if pd.api.types.is_float_dtype(rendered[column]):
            rendered[column] = rendered[column].map(
                lambda value: "" if pd.isna(value) else f"{value:.{digits}f}"
            )
        else:
            rendered[column] = rendered[column].astype(str)
    header = "| " + " | ".join(rendered.columns) + " |"
    separator = "| " + " | ".join(["---"] * len(rendered.columns)) + " |"
    rows = ["| " + " | ".join(row) + " |" for row in rendered.to_numpy(dtype=str)]
    return "\n".join([header, separator] + rows)


def write_report(
    primary: pd.DataFrame,
    validation: pd.DataFrame,
    trajectory: pd.DataFrame,
    summary: pd.DataFrame,
    threshold_summary: pd.DataFrame,
    tests: pd.DataFrame,
    args: argparse.Namespace,
) -> None:
    final_budget = int(trajectory["spice_queries"].max())
    compact = summary[summary["spice_queries"].isin([0, 12, 24, 36, final_budget])][
        [
            "heldout_corner",
            "strategy",
            "spice_queries",
            "runs",
            "median_delay_r2",
            "median_worst_cell_delay_r2",
            "median_top20_recall",
            "median_cumulative_spice_wall_time_s",
        ]
    ]
    thresholds = threshold_summary[
        [
            "heldout_corner",
            "strategy",
            "threshold",
            "runs",
            "reached_runs",
            "median_queries",
            "median_wall_time_s",
            "query_reduction_vs_random_pct",
        ]
    ]
    lines = [
        "# Simulator-in-the-Loop Corner Calibration Report",
        "",
        "## Protocol",
        "",
        f"- Primary V2 rows: {len(primary)}.",
        f"- Independent validation V3 rows: {len(validation)}.",
        f"- Seeds: {', '.join(map(str, args.seeds))}.",
        f"- Held-out corners: {', '.join(args.heldout_corners)}.",
        f"- Candidate points per cell and corner: {args.candidate_per_cell}.",
        f"- Maximum same-corner SPICE queries per run: {args.max_support}.",
        "- Every selected query launched ngspice and retained a netlist and log.",
        "- V3 labels were used only to evaluate each budget and were not available to acquisition strategies.",
        "- The acquisition loop did not use V3 metrics as a stopping or selection signal.",
        f"- Study thresholds: delay R2 >= {args.delay_r2_threshold:.2f}; top-20% recall >= {args.ranking_recall_threshold:.2f}.",
        "",
        "## Budget Trajectories",
        "",
        markdown_table(compact),
        "",
        "## Threshold Crossings",
        "",
        markdown_table(thresholds),
        "",
        "## Paired Two-Sided Wilcoxon Tests",
        "",
        markdown_table(tests),
        "",
        "## Claim Boundary",
        "",
        "This experiment establishes a genuine ngspice-in-the-loop calibration study within the same GF180MCU model and simulator flow. It does not establish cross-PDK, cross-simulator, layout-extracted, or complete Liberty characterization performance.",
    ]
    (args.outdir / "online_spice_corner_calibration_report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def plot_results(summary: pd.DataFrame, threshold_summary: pd.DataFrame, outdir: Path) -> None:
    Path("/private/tmp/matplotlib-cache").mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/matplotlib-cache")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = {
        "random": "#7A7A7A",
        "cell_balanced_random": "#D55E00",
        "space_filling": "#009E73",
        "uncertainty": "#0072B2",
        PROPOSED_STRATEGY: "#CC79A7",
    }
    labels = {
        "random": "Random",
        "cell_balanced_random": "Cell-balanced random",
        "space_filling": "Space-filling",
        "uncertainty": "Uncertainty",
        PROPOSED_STRATEGY: "Cell-balanced space-filling",
    }
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.5))
    aggregated = (
        summary.groupby(["strategy", "spice_queries"])
        .agg(
            delay_r2=("median_delay_r2", "median"),
            worst_cell=("median_worst_cell_delay_r2", "median"),
            recall=("median_top20_recall", "median"),
        )
        .reset_index()
    )
    for strategy in STRATEGIES:
        data = aggregated[aggregated["strategy"] == strategy].sort_values("spice_queries")
        if data.empty:
            continue
        axes[0, 0].plot(data["spice_queries"], data["delay_r2"], marker="o", color=colors[strategy], label=labels[strategy])
        axes[0, 1].plot(data["spice_queries"], data["worst_cell"], marker="o", color=colors[strategy])
        axes[1, 0].plot(data["spice_queries"], data["recall"], marker="o", color=colors[strategy])

    axes[0, 0].set_ylabel(r"Median held-out-corner delay $R^2$")
    axes[0, 1].set_ylabel(r"Median worst-cell delay $R^2$")
    axes[1, 0].set_ylabel("Median top-20% recall")
    for axis in [axes[0, 0], axes[0, 1], axes[1, 0]]:
        axis.set_xlabel("Same-corner SPICE queries")
        axis.grid(True, alpha=0.25)
    axes[0, 0].legend(frameon=False, fontsize=8)

    joint = threshold_summary[threshold_summary["threshold"] == "joint"].copy()
    joint["corner_strategy"] = joint["heldout_corner"] + ":" + joint["strategy"]
    x_positions = np.arange(len(CORNERS))
    width = 0.15
    for strategy_index, strategy in enumerate(STRATEGIES):
        values = []
        for corner in CORNERS:
            subset = joint[(joint["heldout_corner"] == corner) & (joint["strategy"] == strategy)]
            values.append(np.nan if subset.empty else subset["median_queries"].iloc[0])
        axes[1, 1].bar(
            x_positions + (strategy_index - 2) * width,
            values,
            width=width,
            color=colors[strategy],
            label=labels[strategy],
        )
    axes[1, 1].set_xticks(x_positions, CORNERS)
    axes[1, 1].set_xlabel("Held-out process corner")
    axes[1, 1].set_ylabel("Median queries to joint threshold")
    axes[1, 1].grid(True, axis="y", alpha=0.25)

    panel_labels = ["A", "B", "C", "D"]
    for label, axis in zip(panel_labels, axes.ravel()):
        axis.text(-0.12, 1.05, label, transform=axis.transAxes, fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(outdir / "online_spice_corner_calibration.png", dpi=300, bbox_inches="tight")
    fig.savefig(outdir / "online_spice_corner_calibration.pdf", bbox_inches="tight")
    plt.close(fig)


def collect_run_outputs(outdir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    query_files = sorted((outdir / "runs").glob("seed_*/corner_*/*/queries.csv"))
    trajectory_files = sorted((outdir / "runs").glob("seed_*/corner_*/*/trajectory.csv"))
    queries = pd.concat([pd.read_csv(path) for path in query_files], ignore_index=True) if query_files else pd.DataFrame()
    if not queries.empty and "seed" not in queries.columns and "pool_seed" in queries.columns:
        queries["seed"] = queries["pool_seed"].astype(int)
    trajectories = (
        pd.concat([pd.read_csv(path) for path in trajectory_files], ignore_index=True)
        if trajectory_files
        else pd.DataFrame()
    )
    return queries, trajectories


def finalize_outputs(
    primary: pd.DataFrame,
    validation: pd.DataFrame,
    candidate_pools: pd.DataFrame,
    args: argparse.Namespace,
) -> None:
    queries, trajectory = collect_run_outputs(args.outdir)
    if trajectory.empty:
        raise ValueError("No trajectory files were found")
    summary = summarize_trajectory(trajectory)
    crossings = threshold_crossings(trajectory, args)
    threshold_summary = summarize_thresholds(crossings)
    budgets = sorted(set([min(24, args.max_support), args.max_support]))
    tests = paired_tests(trajectory, budgets)

    candidate_pools.to_csv(args.outdir / "online_candidate_pool_features.csv", index=False)
    queries.to_csv(args.outdir / "online_spice_queries.csv", index=False)
    trajectory.to_csv(args.outdir / "online_spice_trajectory.csv", index=False)
    summary.to_csv(args.outdir / "online_spice_budget_summary.csv", index=False)
    crossings.to_csv(args.outdir / "online_spice_threshold_crossings.csv", index=False)
    threshold_summary.to_csv(args.outdir / "online_spice_threshold_summary.csv", index=False)
    tests.to_csv(args.outdir / "online_spice_paired_tests.csv", index=False)
    write_report(primary, validation, trajectory, summary, threshold_summary, tests, args)
    plot_results(summary, threshold_summary, args.outdir)

    metadata = {
        "protocol": "simulator_in_the_loop_unseen_corner_support",
        "primary_rows": int(len(primary)),
        "validation_rows": int(len(validation)),
        "seeds": args.seeds,
        "heldout_corners": args.heldout_corners,
        "strategies": args.strategies,
        "candidate_per_cell": args.candidate_per_cell,
        "batch_size": args.batch_size,
        "max_support": args.max_support,
        "uncertainty_weight": args.uncertainty_weight,
        "diversity_weight": args.diversity_weight,
        "delay_r2_threshold": args.delay_r2_threshold,
        "ranking_recall_threshold": args.ranking_recall_threshold,
        "validation_use": "evaluation_only_not_acquisition",
    }
    (args.outdir / "online_spice_protocol.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    args = parse_args()
    warnings.filterwarnings("ignore", category=UserWarning)
    args.outdir.mkdir(parents=True, exist_ok=True)
    primary = load_spice_dataset(args.primary_dataset)
    validation = load_spice_dataset(args.validation_dataset)

    pools = [
        candidate_pool(seed, corner, args.candidate_per_cell)
        for seed in args.seeds
        for corner in args.heldout_corners
    ]
    candidate_pools = pd.concat(pools, ignore_index=True)

    if not args.summarize_only:
        model_file = find_model_file(args.pdk_root, args.model_file)
        if model_file is None or not model_file.exists():
            raise FileNotFoundError("A real GF180MCU model file is required")
        print(f"model_file={model_file}", flush=True)
        for seed in args.seeds:
            for heldout_corner in args.heldout_corners:
                pool = candidate_pools[
                    (candidate_pools["pool_seed"] == seed)
                    & (candidate_pools["heldout_corner"] == heldout_corner)
                ].copy()
                for strategy in args.strategies:
                    run_one(
                        primary,
                        validation,
                        pool,
                        model_file,
                        seed,
                        heldout_corner,
                        strategy,
                        args,
                    )

    finalize_outputs(primary, validation, candidate_pools, args)
    print(f"Wrote simulator-in-the-loop results to {args.outdir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
