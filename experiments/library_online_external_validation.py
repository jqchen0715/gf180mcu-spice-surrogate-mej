#!/usr/bin/env python3
"""Measured online-corner validation on released GF180MCU standard-cell CDLs."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import qmc
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from spice_v2.gf180_library_cells import (  # noqa: E402
    cdl_device_summary,
    selected_cells,
    simulate_library_point,
)


DEFAULT_ROOT = PROJECT_ROOT / "results" / "gf180_library_external_validation"
DEFAULT_PRIMARY = DEFAULT_ROOT / "primary" / "library_primary.csv"
DEFAULT_VALIDATION = DEFAULT_ROOT / "validation" / "library_validation.csv"
DEFAULT_ONLINE = DEFAULT_ROOT / "online"
CORNER_SEQUENCE = ("typical", "ff", "ss")

NUMERIC_FEATURES = [
    "drive_strength",
    "input_count",
    "transistor_count",
    "total_n_width_um",
    "total_p_width_um",
    "Vdd",
    "Temp",
    "slew_ns",
    "Cload_pF",
]
CATEGORICAL_FEATURES = ["cell_family", "cell_variant", "input_arc", "corner"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--primary", type=Path, default=DEFAULT_PRIMARY)
    parser.add_argument("--validation", type=Path, default=DEFAULT_VALIDATION)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_ONLINE)
    parser.add_argument("--seeds", nargs="*", type=int, default=[0, 1, 2, 3, 4])
    parser.add_argument("--corners", nargs="*", default=list(CORNER_SEQUENCE))
    parser.add_argument("--drives", nargs="*", type=int, default=[1, 4])
    parser.add_argument("--candidate-per-variant", type=int, default=6)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--n-estimators", type=int, default=320)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--summarize-only", action="store_true")
    args = parser.parse_args()
    for name in ("primary", "validation", "outdir"):
        setattr(args, name, getattr(args, name).expanduser().resolve())
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


def load_dataset(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = set(FEATURES + ["delay_avg_ns", "power_avg_uW", "status", "fidelity"])
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{path} is missing columns: {missing}")
    frame = frame[
        frame["status"].eq("ok")
        & frame["fidelity"].eq("SPICE_GF180MCU_RELEASED_CDL")
    ].copy()
    if frame.empty:
        raise ValueError(f"No released-CDL SPICE rows in {path}")
    return frame.reset_index(drop=True)


def candidate_pool(seed: int, corner: str, drives: tuple[int, ...], points_per_variant: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    cells = selected_cells(drives)
    corner_index = CORNER_SEQUENCE.index(corner)
    for cell_index, cell in enumerate(cells):
        sampler = qmc.LatinHypercube(d=4, seed=20260801 + seed * 1009 + corner_index * 137 + cell_index)
        unit = sampler.random(n=points_per_variant)
        points = qmc.scale(unit, [1.62, -40.0, 0.02, 0.001], [1.98, 125.0, 12.0, 0.2059])
        device = cdl_device_summary(cell)
        for vdd, temp, slew, cload in points:
            rows.append(
                {
                    "cell_family": cell.family.upper(),
                    "cell_variant": cell.variant.upper(),
                    "drive_strength": cell.drive,
                    "input_arc": cell.input_arc,
                    "inverting": int(cell.inverting),
                    "input_count": len(cell.pins) - 1,
                    **device,
                    "Vdd": float(vdd),
                    "Temp": float(temp),
                    "slew_ns": float(slew),
                    "Cload_pF": float(cload),
                    "corner": corner,
                    "seed": seed,
                    "heldout_corner": corner,
                }
            )
    frame = pd.DataFrame(rows)
    frame.insert(0, "candidate_id", np.arange(len(frame), dtype=int))
    return frame


def geometry(pool: pd.DataFrame) -> np.ndarray:
    values = pool[["Vdd", "Temp", "slew_ns", "Cload_pF"]].to_numpy(dtype=float)
    scale = values.std(axis=0)
    scale[scale <= 1e-15] = 1.0
    return (values - values.mean(axis=0)) / scale


def balanced_space_filling_order(pool: pd.DataFrame) -> list[int]:
    matrix = geometry(pool)
    order: list[int] = []
    variants = sorted(pool["cell_variant"].unique())
    selected_by_variant: dict[str, list[int]] = {variant: [] for variant in variants}
    remaining_by_variant = {
        variant: pool.index[pool["cell_variant"].eq(variant)].astype(int).tolist()
        for variant in variants
    }
    while any(remaining_by_variant.values()):
        for variant in variants:
            remaining = remaining_by_variant[variant]
            if not remaining:
                continue
            selected = selected_by_variant[variant]
            if selected:
                distances = np.sqrt(
                    ((matrix[np.asarray(remaining)][:, None, :] - matrix[np.asarray(selected)][None, :, :]) ** 2).sum(axis=2)
                ).min(axis=1)
            else:
                variant_points = matrix[np.asarray(remaining)]
                distances = np.sqrt(((variant_points - variant_points.mean(axis=0)) ** 2).sum(axis=1))
            pick = remaining[int(np.argmax(distances))]
            order.append(int(pool.loc[pick, "candidate_id"]))
            selected.append(pick)
            remaining.remove(pick)
    return order


def simulate_pool(pool: pd.DataFrame, order: list[int], args: argparse.Namespace, seed: int, corner: str) -> pd.DataFrame:
    run_dir = args.outdir / "runs" / f"seed_{seed}" / f"corner_{corner}"
    output = run_dir / "measured_pool_96.csv"
    if args.resume and output.exists():
        frame = pd.read_csv(output)
        if len(frame) == len(pool) and frame["status"].eq("ok").all():
            return frame.sort_values("query_order").reset_index(drop=True)
    run_dir.mkdir(parents=True, exist_ok=True)
    cells = {cell.variant.upper(): cell for cell in selected_cells(tuple(args.drives))}
    tasks = []
    for query_order, candidate_id in enumerate(order, start=1):
        candidate = pool.loc[pool["candidate_id"].eq(candidate_id)].iloc[0]
        cell = cells[str(candidate["cell_variant"])]
        sample_id = 10_000_000 + seed * 100_000 + CORNER_SEQUENCE.index(corner) * 10_000 + query_order
        tasks.append((query_order, candidate, cell, sample_id))

    rows = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {
            executor.submit(
                simulate_library_point,
                cell,
                sample_id,
                corner,
                float(candidate["Vdd"]),
                float(candidate["Temp"]),
                float(candidate["slew_ns"]),
                float(candidate["Cload_pF"]),
                run_dir / "netlists",
                run_dir / "logs",
            ): (query_order, candidate)
            for query_order, candidate, cell, sample_id in tasks
        }
        for future in as_completed(futures):
            query_order, candidate = futures[future]
            row = future.result()
            row.update(
                {
                    "candidate_id": int(candidate["candidate_id"]),
                    "seed": seed,
                    "heldout_corner": corner,
                    "query_order": query_order,
                    "batch_index": int(math.ceil(query_order / len(cells))),
                }
            )
            rows.append(row)
            print(f"library pool seed={seed} corner={corner} {query_order}/{len(pool)} {row['status']}", flush=True)
    frame = pd.DataFrame(rows).sort_values("query_order").reset_index(drop=True)
    frame.to_csv(output, index=False)
    if not frame["status"].eq("ok").all():
        raise RuntimeError(f"SPICE failures in {output}")
    return frame


def robust_scale(values: pd.Series) -> float:
    q25, q75 = np.quantile(values.to_numpy(dtype=float), [0.25, 0.75])
    return max(float(q75 - q25), float(np.median(np.abs(values))) * 0.1, 1e-12)


def fit_delay(train: pd.DataFrame, seed: int, n_estimators: int) -> Pipeline:
    model = build_model(seed, n_estimators)
    model.fit(train[FEATURES], train["delay_avg_ns"])
    return model


def evaluate_pool(
    primary: pd.DataFrame,
    validation: pd.DataFrame,
    measured: pd.DataFrame,
    seed: int,
    corner: str,
    n_estimators: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = primary[primary["corner"].ne(corner)].copy().reset_index(drop=True)
    target = validation[validation["corner"].eq(corner)].copy().reset_index(drop=True)
    variants = sorted(measured["cell_variant"].unique())
    batch_size = len(variants)
    rows: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    initial_radius = None
    previous_pool_predictions = None

    for budget in range(0, len(measured) + 1, batch_size):
        support = measured.iloc[:budget].copy()
        train = base if support.empty else pd.concat([base, support], ignore_index=True)
        # Hold estimator randomness fixed within a pool so that the
        # prediction-change diagnostic reflects newly acquired SPICE support
        # rather than a different random forest realization at each budget.
        model = fit_delay(train, seed, n_estimators)
        prediction = model.predict(target[FEATURES])
        variant_r2 = []
        for variant in variants:
            mask = target["cell_variant"].eq(variant)
            if mask.sum() >= 2:
                variant_r2.append(float(r2_score(target.loc[mask, "delay_avg_ns"], prediction[mask.to_numpy()])))
        family_r2 = []
        for family in sorted(target["cell_family"].unique()):
            mask = target["cell_family"].eq(family)
            if mask.sum() >= 2:
                family_r2.append(float(r2_score(target.loc[mask, "delay_avg_ns"], prediction[mask.to_numpy()])))
        row = {
            "seed": seed,
            "heldout_corner": corner,
            "support_budget": budget,
            "delay_r2": float(r2_score(target["delay_avg_ns"], prediction)),
            "delay_mae_ns": float(mean_absolute_error(target["delay_avg_ns"], prediction)),
            "worst_family_delay_r2": float(min(family_r2)),
            "worst_variant_delay_r2": float(min(variant_r2)),
            "cumulative_spice_wall_time_s": float(support["spice_wall_time_s"].sum()) if not support.empty else 0.0,
        }

        pool_features = measured[FEATURES]
        current_pool_predictions = model.predict(pool_features)
        change = float("nan")
        if previous_pool_predictions is not None:
            change = float(np.median(np.abs(current_pool_predictions - previous_pool_predictions)) / robust_scale(train["delay_avg_ns"]))
        previous_pool_predictions = current_pool_predictions

        chosen_ids = measured.iloc[:budget]["candidate_id"].astype(int).tolist()
        remaining_ids = measured.iloc[budget:]["candidate_id"].astype(int).tolist()
        # Candidate IDs are assigned before acquisition; measured rows are stored
        # in query order. Re-sort before using candidate IDs as matrix positions.
        pool_geometry = geometry(measured.sort_values("candidate_id").reset_index(drop=True))
        if not remaining_ids:
            radius = 0.0
        elif chosen_ids:
            distances = np.sqrt(
                ((pool_geometry[np.asarray(remaining_ids)][:, None, :] - pool_geometry[np.asarray(chosen_ids)][None, :, :]) ** 2).sum(axis=2)
            )
            radius = float(distances.min(axis=1).max())
        else:
            radius = float(np.sqrt(((pool_geometry - pool_geometry.mean(axis=0)) ** 2).sum(axis=1)).max())
        if initial_radius is None:
            initial_radius = radius
        coverage_ratio = radius / initial_radius if initial_radius > 0 else 0.0

        prequential_nmae = float("nan")
        if budget > 0:
            batch = measured.iloc[budget - batch_size : budget]
            prior_support = measured.iloc[: budget - batch_size]
            prior_train = base if prior_support.empty else pd.concat([base, prior_support], ignore_index=True)
            prior_model = fit_delay(prior_train, seed, n_estimators)
            batch_pred = prior_model.predict(batch[FEATURES])
            prequential_nmae = float(
                mean_absolute_error(batch["delay_avg_ns"], batch_pred) / robust_scale(prior_train["delay_avg_ns"])
            )
        row.update(
            {
                "prequential_delay_nmae": prequential_nmae,
                "prediction_change_nmae": change,
                "coverage_radius_ratio": coverage_ratio,
            }
        )
        rows.append(row)
        diagnostics.append(
            {
                "seed": seed,
                "heldout_corner": corner,
                "support_budget": budget,
                "prequential_delay_nmae": prequential_nmae,
                "prediction_change_nmae": change,
                "coverage_radius_ratio": coverage_ratio,
            }
        )
    trajectory = pd.DataFrame(rows)
    full_r2 = float(trajectory.iloc[-1]["delay_r2"])
    trajectory["delay_r2_gap_to_full"] = full_r2 - trajectory["delay_r2"]
    return trajectory, pd.DataFrame(diagnostics)


def write_summary(trajectory: pd.DataFrame, outdir: Path) -> None:
    summary = (
        trajectory.groupby(["heldout_corner", "support_budget"], as_index=False)
        .agg(
            runs=("seed", "size"),
            median_delay_r2=("delay_r2", "median"),
            q25_delay_r2=("delay_r2", lambda s: s.quantile(0.25)),
            q75_delay_r2=("delay_r2", lambda s: s.quantile(0.75)),
            median_gap_to_full=("delay_r2_gap_to_full", "median"),
            median_worst_family_r2=("worst_family_delay_r2", "median"),
            median_worst_variant_r2=("worst_variant_delay_r2", "median"),
            median_spice_time_s=("cumulative_spice_wall_time_s", "median"),
        )
    )
    summary.to_csv(outdir / "library_online_budget_summary.csv", index=False)
    pooled = (
        trajectory.groupby("support_budget", as_index=False)
        .agg(
            runs=("seed", "size"),
            median_delay_r2=("delay_r2", "median"),
            median_gap_to_full=("delay_r2_gap_to_full", "median"),
            median_worst_family_r2=("worst_family_delay_r2", "median"),
            median_worst_variant_r2=("worst_variant_delay_r2", "median"),
            median_spice_time_s=("cumulative_spice_wall_time_s", "median"),
        )
    )
    pooled.to_csv(outdir / "library_online_pooled_summary.csv", index=False)
    protocol = {
        "dataset_role": "released GF180MCU 7-track CDL external validation",
        "cell_families": sorted(cell.family.upper() for cell in selected_cells((1,))),
        "candidate_pool_size": 96,
        "acquisition": "cell-variant-balanced farthest-first space coverage",
        "validation_labels_visible_to_acquisition": False,
        "estimator_random_state_policy": "fixed to the pool seed at every support budget",
        "full_reference": "all 96 candidate netlists measured with ngspice",
        "development_seeds_for_stopping": [0, 1, 2],
        "locked_confirmation_seeds_for_stopping": [3, 4],
    }
    (outdir / "library_online_protocol.json").write_text(json.dumps(protocol, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    primary = load_dataset(args.primary)
    validation = load_dataset(args.validation)
    trajectories = []
    diagnostics = []
    pools = []
    for seed in args.seeds:
        for corner in args.corners:
            pool = candidate_pool(seed, corner, tuple(args.drives), args.candidate_per_variant)
            order = balanced_space_filling_order(pool)
            pool["query_order"] = pool["candidate_id"].map({cid: i + 1 for i, cid in enumerate(order)})
            pools.append(pool)
            measured_path = args.outdir / "runs" / f"seed_{seed}" / f"corner_{corner}" / "measured_pool_96.csv"
            if args.summarize_only:
                measured = pd.read_csv(measured_path)
            else:
                measured = simulate_pool(pool, order, args, seed, corner)
            trajectory, diagnostic = evaluate_pool(primary, validation, measured, seed, corner, args.n_estimators)
            trajectories.append(trajectory)
            diagnostics.append(diagnostic)
    all_pools = pd.concat(pools, ignore_index=True)
    all_trajectory = pd.concat(trajectories, ignore_index=True)
    all_diagnostics = pd.concat(diagnostics, ignore_index=True)
    all_pools.to_csv(args.outdir / "library_online_candidate_features.csv", index=False)
    all_trajectory.to_csv(args.outdir / "library_online_trajectory.csv", index=False)
    all_diagnostics.to_csv(args.outdir / "library_online_internal_diagnostics.csv", index=False)
    write_summary(all_trajectory, args.outdir)
    print(all_trajectory.groupby("support_budget")["delay_r2"].median().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
