#!/usr/bin/env python3
"""Prospectively confirm the locked stopping rule on new GF180MCU/SKY130 pools.

For every PDK/corner pool, the program commits code and rule hashes, simulates
one 16-variant batch at a time, and writes an immutable decision snapshot before
running any post-decision calls needed to construct the 96-call reference.  The
validation dataset is not loaded until the decision artifact exists.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import sys
from typing import Any, Callable

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.library_online_external_validation import (  # noqa: E402
    CORNER_SEQUENCE,
    FEATURES,
    balanced_space_filling_order,
    candidate_pool as gf_candidate_pool,
    evaluate_pool,
    fit_delay,
    geometry,
    load_dataset as load_gf_dataset,
    robust_scale,
)
from experiments.sky130_cross_pdk_protocol_replication import (  # noqa: E402
    EXPECTED_LOCKED_RULE,
    candidate_pool as sky_candidate_pool,
    load_dataset as load_sky_dataset,
)
from spice_v2.gf180_library_cells import (  # noqa: E402
    selected_cells as gf_selected_cells,
    simulate_library_point as simulate_gf_point,
)
from spice_v2.sky130_library_cells import (  # noqa: E402
    selected_cells as sky_selected_cells,
    simulate_library_point as simulate_sky_point,
)


DEFAULT_OUTDIR = PROJECT_ROOT / "results" / "prospective_locked_confirmation"
GF_PRIMARY = PROJECT_ROOT / "results/gf180_library_external_validation/primary/library_primary.csv"
GF_VALIDATION = PROJECT_ROOT / "results/gf180_library_external_validation/validation/library_validation.csv"
SKY_PRIMARY = PROJECT_ROOT / "results/sky130_cross_pdk_replication/primary/sky130_library_primary.csv"
SKY_VALIDATION = PROJECT_ROOT / "results/sky130_cross_pdk_replication/validation/sky130_library_validation.csv"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--pdks", nargs="*", choices=["gf180", "sky130"], default=["gf180", "sky130"])
    parser.add_argument("--corners", nargs="*", choices=list(CORNER_SEQUENCE), default=list(CORNER_SEQUENCE))
    parser.add_argument("--seed", type=int, default=5)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--n-estimators", type=int, default=320)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    args.outdir = args.outdir.expanduser().resolve()
    return args


def pdk_configuration(pdk: str) -> dict[str, Any]:
    if pdk == "gf180":
        return {
            "label": "GF180MCU",
            "candidate_pool": gf_candidate_pool,
            "selected_cells": gf_selected_cells,
            "simulate_point": simulate_gf_point,
            "load_dataset": load_gf_dataset,
            "primary_path": GF_PRIMARY,
            "validation_path": GF_VALIDATION,
            "simulator_source": PROJECT_ROOT / "spice_v2/gf180_library_cells.py",
            "sample_base": 21_000_000,
        }
    return {
        "label": "SKY130",
        "candidate_pool": sky_candidate_pool,
        "selected_cells": sky_selected_cells,
        "simulate_point": simulate_sky_point,
        "load_dataset": load_sky_dataset,
        "primary_path": SKY_PRIMARY,
        "validation_path": SKY_VALIDATION,
        "simulator_source": PROJECT_ROOT / "spice_v2/sky130_library_cells.py",
        "sample_base": 26_000_000,
    }


def write_precommit_manifest(run_dir: Path, config: dict[str, Any], seed: int, corner: str) -> dict[str, Any]:
    path = run_dir / "precommit_manifest.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    sources = [
        Path(__file__).resolve(),
        PROJECT_ROOT / "experiments/library_online_external_validation.py",
        config["simulator_source"],
    ]
    manifest = {
        "committed_at_utc": utc_now(),
        "study_role": "prospective sequential confirmation after threshold lock",
        "pdk": config["label"],
        "seed": seed,
        "heldout_corner": corner,
        "locked_rule": EXPECTED_LOCKED_RULE,
        "two_consecutive_eligible_batches_required": True,
        "candidate_pool_size": 96,
        "batch_size": 16,
        "estimator_random_state": seed,
        "source_sha256": {str(source.relative_to(PROJECT_ROOT)): sha256(source) for source in sources},
        "primary_training_data_sha256": sha256(config["primary_path"]),
        "validation_path_declared_but_not_opened_before_decision": str(
            config["validation_path"].relative_to(PROJECT_ROOT)
        ),
        "python": platform.python_version(),
    }
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def coverage_ratio(pool: pd.DataFrame, measured: pd.DataFrame) -> float:
    matrix = geometry(pool.sort_values("candidate_id").reset_index(drop=True))
    selected = measured["candidate_id"].astype(int).tolist()
    remaining = sorted(set(pool["candidate_id"].astype(int)) - set(selected))
    initial = float(np.sqrt(((matrix - matrix.mean(axis=0)) ** 2).sum(axis=1)).max())
    if not remaining:
        radius = 0.0
    elif selected:
        distances = np.sqrt(
            ((matrix[np.asarray(remaining)][:, None, :] - matrix[np.asarray(selected)][None, :, :]) ** 2).sum(axis=2)
        )
        radius = float(distances.min(axis=1).max())
    else:
        radius = initial
    return radius / initial if initial > 0 else 0.0


def simulate_batch(
    pdk: str,
    config: dict[str, Any],
    pool: pd.DataFrame,
    candidate_ids: list[int],
    query_order: dict[int, int],
    run_dir: Path,
    seed: int,
    corner: str,
    workers: int,
    phase: str,
) -> pd.DataFrame:
    cells = {cell.variant.upper(): cell for cell in config["selected_cells"]((1, 4))}
    simulate_point: Callable[..., dict[str, Any]] = config["simulate_point"]
    tasks: list[tuple[int, pd.Series, Any, int]] = []
    for candidate_id in candidate_ids:
        candidate = pool.loc[pool["candidate_id"].eq(candidate_id)].iloc[0]
        order = query_order[candidate_id]
        sample_id = config["sample_base"] + seed * 100_000 + CORNER_SEQUENCE.index(corner) * 10_000 + order
        tasks.append((order, candidate, cells[str(candidate["cell_variant"])], sample_id))
    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {
            executor.submit(
                simulate_point,
                cell,
                sample_id,
                corner,
                float(candidate["Vdd"]),
                float(candidate["Temp"]),
                float(candidate["slew_ns"]),
                float(candidate["Cload_pF"]),
                run_dir / "netlists",
                run_dir / "logs",
            ): (order, candidate)
            for order, candidate, cell, sample_id in tasks
        }
        for future in as_completed(futures):
            order, candidate = futures[future]
            row = future.result()
            row.update(
                {
                    "candidate_id": int(candidate["candidate_id"]),
                    "seed": seed,
                    "heldout_corner": corner,
                    "query_order": order,
                    "batch_index": int(math.ceil(order / 16)),
                    "acquisition_phase": phase,
                }
            )
            rows.append(row)
            print(
                f"prospective {pdk} seed={seed} corner={corner} query={order}/96 {row['status']}",
                flush=True,
            )
    batch = pd.DataFrame(rows).sort_values("query_order").reset_index(drop=True)
    if not batch["status"].eq("ok").all():
        raise RuntimeError(f"SPICE failure in {pdk} seed={seed} corner={corner}")
    return batch


def replay_observables(
    primary: pd.DataFrame,
    pool: pd.DataFrame,
    measured: pd.DataFrame,
    seed: int,
    corner: str,
    n_estimators: int,
) -> pd.DataFrame:
    base = primary[primary["corner"].ne(corner)].copy().reset_index(drop=True)
    pool_features = pool[FEATURES]
    rows: list[dict[str, Any]] = []
    previous_predictions = None
    previous_eligible = False
    maximum_budget = len(measured) // 16 * 16
    for budget in range(0, maximum_budget + 1, 16):
        support = measured.iloc[:budget]
        train = base if support.empty else pd.concat([base, support], ignore_index=True)
        model = fit_delay(train, seed, n_estimators)
        predictions = model.predict(pool_features)
        change = float("nan")
        if previous_predictions is not None:
            change = float(np.median(np.abs(predictions - previous_predictions)) / robust_scale(train["delay_avg_ns"]))
        previous_predictions = predictions
        prequential = float("nan")
        if budget > 0:
            batch = measured.iloc[budget - 16 : budget]
            prior_support = measured.iloc[: budget - 16]
            prior_train = base if prior_support.empty else pd.concat([base, prior_support], ignore_index=True)
            prior_model = fit_delay(prior_train, seed, n_estimators)
            prequential = float(
                mean_absolute_error(batch["delay_avg_ns"], prior_model.predict(batch[FEATURES]))
                / robust_scale(prior_train["delay_avg_ns"])
            )
        coverage = coverage_ratio(pool, support)
        eligible = bool(
            budget >= int(EXPECTED_LOCKED_RULE["minimum_budget"])
            and prequential <= float(EXPECTED_LOCKED_RULE["prequential_nmae_threshold"])
            and change <= float(EXPECTED_LOCKED_RULE["prediction_change_threshold"])
            and coverage <= float(EXPECTED_LOCKED_RULE["coverage_ratio_threshold"])
        )
        rows.append(
            {
                "support_budget": budget,
                "prequential_delay_nmae": prequential,
                "prediction_change_nmae": change,
                "coverage_radius_ratio": coverage,
                "eligible": eligible,
                "two_consecutive_eligible": bool(eligible and previous_eligible),
            }
        )
        previous_eligible = eligible
    return pd.DataFrame(rows)


def run_pool(pdk: str, seed: int, corner: str, args: argparse.Namespace) -> dict[str, Any]:
    config = pdk_configuration(pdk)
    run_dir = args.outdir / pdk / f"seed_{seed}" / f"corner_{corner}"
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = write_precommit_manifest(run_dir, config, seed, corner)
    pool = config["candidate_pool"](seed, corner, (1, 4), 6)
    order = balanced_space_filling_order(pool)
    query_order = {candidate_id: index + 1 for index, candidate_id in enumerate(order)}
    pool["query_order"] = pool["candidate_id"].map(query_order)
    pool = pool.sort_values("query_order").reset_index(drop=True)
    pool_path = run_dir / "candidate_features.csv"
    if not pool_path.exists():
        pool.to_csv(pool_path, index=False)

    measurements_path = run_dir / "sequential_measurements.csv"
    if args.resume and measurements_path.exists():
        measured = pd.read_csv(measurements_path).sort_values("query_order").reset_index(drop=True)
    else:
        measured = pd.DataFrame()
    decision_path = run_dir / "decision_record.json"
    decision = json.loads(decision_path.read_text(encoding="utf-8")) if decision_path.exists() else None
    primary = config["load_dataset"](config["primary_path"])

    for start in range(len(measured), 96, 16):
        candidate_ids = pool.iloc[start : start + 16]["candidate_id"].astype(int).tolist()
        phase = "reference_completion" if decision is not None else "stopping_evaluation"
        batch = simulate_batch(
            pdk, config, pool, candidate_ids, query_order, run_dir, seed, corner, args.workers, phase
        )
        measured = pd.concat([measured, batch], ignore_index=True).sort_values("query_order").reset_index(drop=True)
        measured.to_csv(measurements_path, index=False)

        if decision is None:
            observables = replay_observables(primary, pool, measured, seed, corner, args.n_estimators)
            observables.to_csv(run_dir / "online_observables.csv", index=False)
            latest = observables.iloc[-1]
            triggered = bool(latest["two_consecutive_eligible"])
            fallback = len(measured) == 96 and not triggered
            if triggered or fallback:
                measured.iloc[: len(measured)].to_csv(run_dir / "decision_snapshot.csv", index=False)
                decision = {
                    "decision_written_at_utc": utc_now(),
                    "pdk": config["label"],
                    "seed": seed,
                    "heldout_corner": corner,
                    "decision_budget": int(len(measured)),
                    "decision_type": "two_consecutive_eligible_batches" if triggered else "full_budget_fallback",
                    "latest_observables": {
                        "prequential_delay_nmae": float(latest["prequential_delay_nmae"]),
                        "prediction_change_nmae": float(latest["prediction_change_nmae"]),
                        "coverage_radius_ratio": float(latest["coverage_radius_ratio"]),
                    },
                    "locked_rule": EXPECTED_LOCKED_RULE,
                    "precommit_manifest_sha256": sha256(run_dir / "precommit_manifest.json"),
                    "candidate_features_sha256": sha256(pool_path),
                    "decision_snapshot_sha256": sha256(run_dir / "decision_snapshot.csv"),
                    "validation_labels_opened_before_decision": False,
                }
                decision_path.write_text(json.dumps(decision, indent=2), encoding="utf-8")
                print(f"DECISION {pdk} {corner}: {decision['decision_type']} at {len(measured)}/96", flush=True)

    if decision is None:
        raise RuntimeError(f"No decision artifact for {pdk} seed={seed} corner={corner}")
    completion = {
        "reference_completed_at_utc": utc_now(),
        "decision_record_sha256": sha256(decision_path),
        "measured_pool_96_sha256": sha256(measurements_path),
        "post_decision_calls": 96 - int(decision["decision_budget"]),
        "manifest_source_hashes_preserved": manifest["source_sha256"],
    }
    (run_dir / "reference_completion_record.json").write_text(
        json.dumps(completion, indent=2), encoding="utf-8"
    )

    # Validation labels are first opened here, after decision_record.json exists.
    validation = config["load_dataset"](config["validation_path"])
    trajectory, _ = evaluate_pool(primary, validation, measured, seed, corner, args.n_estimators)
    trajectory.to_csv(run_dir / "post_decision_validation_trajectory.csv", index=False)
    chosen = trajectory[trajectory["support_budget"].eq(int(decision["decision_budget"]))].iloc[0]
    return {
        "pdk": config["label"],
        "seed": seed,
        "heldout_corner": corner,
        "decision_budget": int(decision["decision_budget"]),
        "decision_type": decision["decision_type"],
        "query_reduction_pct": 100.0 * (96 - int(decision["decision_budget"])) / 96,
        "delay_r2": float(chosen["delay_r2"]),
        "full_delay_r2": float(trajectory.iloc[-1]["delay_r2"]),
        "delay_r2_gap_to_full": float(chosen["delay_r2_gap_to_full"]),
        "gap_le_0p02": bool(chosen["delay_r2_gap_to_full"] <= 0.02),
        "worst_family_delay_r2": float(chosen["worst_family_delay_r2"]),
        "worst_variant_delay_r2": float(chosen["worst_variant_delay_r2"]),
        "cumulative_spice_wall_time_s": float(chosen["cumulative_spice_wall_time_s"]),
        "full_cumulative_spice_wall_time_s": float(trajectory.iloc[-1]["cumulative_spice_wall_time_s"]),
        "decision_record": str(decision_path.relative_to(PROJECT_ROOT)),
    }


def main() -> int:
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    results = []
    for pdk in args.pdks:
        for corner in args.corners:
            results.append(run_pool(pdk, args.seed, corner, args))
    frame = pd.DataFrame(results)
    frame.to_csv(args.outdir / "prospective_confirmation_results.csv", index=False)
    summary = (
        frame.groupby("pdk", as_index=False)
        .agg(
            pools=("seed", "size"),
            early_stopped_pools=("decision_budget", lambda values: int((values < 96).sum())),
            median_decision_budget=("decision_budget", "median"),
            calls_avoided=("decision_budget", lambda values: int((96 - values).sum())),
            gap_le_0p02_successes=("gap_le_0p02", "sum"),
            maximum_gap_to_full=("delay_r2_gap_to_full", "max"),
            median_delay_r2=("delay_r2", "median"),
            median_worst_family_r2=("worst_family_delay_r2", "median"),
            median_worst_variant_r2=("worst_variant_delay_r2", "median"),
        )
    )
    summary.to_csv(args.outdir / "prospective_confirmation_summary.csv", index=False)
    protocol = {
        "study_role": "prospective new-pool confirmation",
        "seed": args.seed,
        "locked_rule": EXPECTED_LOCKED_RULE,
        "validation_labels_visible_before_decision": False,
        "decision_artifact_written_before_reference_completion": True,
        "results": results,
    }
    (args.outdir / "prospective_confirmation_protocol_and_results.json").write_text(
        json.dumps(protocol, indent=2), encoding="utf-8"
    )
    print(summary.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
