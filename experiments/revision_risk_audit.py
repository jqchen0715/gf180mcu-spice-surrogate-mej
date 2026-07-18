#!/usr/bin/env python3
"""Generate reviewer-facing robustness diagnostics for the stopping protocol.

The audit consumes measured pools that already exist on disk.  It never uses
validation labels to choose support points or a stopping decision.  Validation
labels are opened only after a budget has been selected, to quantify the loss
relative to the completed 96-call reference.
"""

from __future__ import annotations

from itertools import product
import json
import math
from pathlib import Path
import sys
from time import perf_counter

import numpy as np
import pandas as pd
from scipy.stats import beta, spearmanr
from sklearn.metrics import mean_absolute_error, r2_score


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
OUTDIR = PROJECT_ROOT / "results" / "revision_risk_audit"
GF_ROOT = PROJECT_ROOT / "results" / "gf180_library_external_validation"
SKY_ROOT = PROJECT_ROOT / "results" / "sky130_cross_pdk_replication"

from experiments.library_online_external_validation import (  # noqa: E402
    FEATURES,
    fit_delay,
    load_dataset as load_gf_dataset,
    robust_scale,
)
from experiments.sky130_cross_pdk_protocol_replication import (  # noqa: E402
    EXPECTED_LOCKED_RULE,
    load_dataset as load_sky_dataset,
)


def clopper_pearson(successes: int, trials: int, alpha: float = 0.05) -> tuple[float, float]:
    if trials == 0:
        return float("nan"), float("nan")
    lower = 0.0 if successes == 0 else float(beta.ppf(alpha / 2, successes, trials - successes + 1))
    upper = 1.0 if successes == trials else float(beta.ppf(1 - alpha / 2, successes + 1, trials - successes))
    return lower, upper


def stop_budget(run: pd.DataFrame, signals: tuple[str, ...], rule: dict[str, float | int]) -> int:
    ordered = run.sort_values("support_budget").reset_index(drop=True)
    eligible = ordered["support_budget"].ge(int(rule["minimum_budget"]))
    definitions = {
        "prequential": ordered["prequential_delay_nmae"].le(float(rule["prequential_nmae_threshold"])),
        "prediction_change": ordered["prediction_change_nmae"].le(float(rule["prediction_change_threshold"])),
        "coverage": ordered["coverage_radius_ratio"].le(float(rule["coverage_ratio_threshold"])),
    }
    for signal in signals:
        eligible &= definitions[signal]
    consecutive = eligible & eligible.shift(1, fill_value=False)
    if consecutive.any():
        return int(ordered.loc[consecutive, "support_budget"].iloc[0])
    return int(ordered["support_budget"].max())


def decision_rows(
    trajectory: pd.DataFrame,
    pdk: str,
    cohort: str,
    method: str,
    signals: tuple[str, ...] = (),
    fixed_budget: int | None = None,
    rule: dict[str, float | int] | None = None,
) -> pd.DataFrame:
    selected_rule = EXPECTED_LOCKED_RULE if rule is None else rule
    rows: list[dict[str, object]] = []
    for (seed, corner), run in trajectory.groupby(["seed", "heldout_corner"], sort=True):
        budget = fixed_budget if fixed_budget is not None else stop_budget(run, signals, selected_rule)
        chosen = run.loc[run["support_budget"].eq(budget)].iloc[0]
        rows.append(
            {
                "pdk": pdk,
                "cohort": cohort,
                "method": method,
                "seed": int(seed),
                "heldout_corner": str(corner),
                "stop_budget": int(budget),
                "early_stopped": bool(budget < 96),
                "query_reduction_pct": 100.0 * (96 - int(budget)) / 96,
                "delay_r2": float(chosen["delay_r2"]),
                "full_delay_r2": float(run.loc[run["support_budget"].eq(96), "delay_r2"].iloc[0]),
                "delay_r2_gap_to_full": float(chosen["delay_r2_gap_to_full"]),
                "gap_le_0p02": bool(chosen["delay_r2_gap_to_full"] <= 0.02),
                "gap_le_0p05": bool(chosen["delay_r2_gap_to_full"] <= 0.05),
                "worst_family_delay_r2": float(chosen["worst_family_delay_r2"]),
                "worst_variant_delay_r2": float(chosen["worst_variant_delay_r2"]),
                "cumulative_spice_wall_time_s": float(chosen["cumulative_spice_wall_time_s"]),
                "full_cumulative_spice_wall_time_s": float(
                    run.loc[run["support_budget"].eq(96), "cumulative_spice_wall_time_s"].iloc[0]
                ),
            }
        )
    return pd.DataFrame(rows)


def summarize_decisions(rows: pd.DataFrame, subset: str) -> dict[str, object]:
    if subset == "early_stop_only":
        data = rows[rows["early_stopped"]].copy()
    elif subset == "full_budget_fallback":
        data = rows[~rows["early_stopped"]].copy()
    else:
        data = rows.copy()
    n = int(len(data))
    successes = int(data["gap_le_0p02"].sum()) if n else 0
    lower, upper = clopper_pearson(successes, n)
    return {
        "pdk": rows["pdk"].iloc[0],
        "cohort": rows["cohort"].iloc[0],
        "method": rows["method"].iloc[0],
        "subset": subset,
        "runs": n,
        "successful_runs": successes,
        "gap_le_0p02_rate": successes / n if n else float("nan"),
        "exact_95ci_lower": lower,
        "exact_95ci_upper": upper,
        "median_stop_budget": float(data["stop_budget"].median()) if n else float("nan"),
        "median_query_reduction_pct": float(data["query_reduction_pct"].median()) if n else float("nan"),
        "median_gap_to_full": float(data["delay_r2_gap_to_full"].median()) if n else float("nan"),
        "maximum_gap_to_full": float(data["delay_r2_gap_to_full"].max()) if n else float("nan"),
        "median_worst_family_r2": float(data["worst_family_delay_r2"].median()) if n else float("nan"),
        "median_worst_variant_r2": float(data["worst_variant_delay_r2"].median()) if n else float("nan"),
    }


def top_fraction_recall(y_true: np.ndarray, prediction: np.ndarray, fraction: float = 0.2) -> float:
    count = max(1, int(math.ceil(len(y_true) * fraction)))
    actual = set(np.argsort(y_true)[-count:].tolist())
    predicted = set(np.argsort(prediction)[-count:].tolist())
    return len(actual & predicted) / count


def evaluate_selected_budgets(
    pdk: str,
    primary: pd.DataFrame,
    validation: pd.DataFrame,
    decisions: pd.DataFrame,
    online_root: Path,
    n_estimators: int = 320,
    measurement_filename: str = "measured_pool_96.csv",
    runs_subdir: str = "runs",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    variant_rows: list[dict[str, object]] = []
    pool_rows: list[dict[str, object]] = []
    for decision in decisions.itertuples(index=False):
        run_root = online_root / runs_subdir if runs_subdir else online_root
        measured_path = (
            run_root
            / f"seed_{decision.seed}"
            / f"corner_{decision.heldout_corner}"
            / measurement_filename
        )
        measured = pd.read_csv(measured_path).sort_values("query_order").reset_index(drop=True)
        base = primary[primary["corner"].ne(decision.heldout_corner)].copy().reset_index(drop=True)
        target = validation[validation["corner"].eq(decision.heldout_corner)].copy().reset_index(drop=True)
        for evaluation_stage, budget in (("stopped", int(decision.stop_budget)), ("full_96", 96)):
            support = measured.iloc[:budget].copy()
            train = pd.concat([base, support], ignore_index=True)
            start = perf_counter()
            model = fit_delay(train, int(decision.seed), n_estimators)
            fit_time = perf_counter() - start
            start = perf_counter()
            prediction = model.predict(target[FEATURES])
            predict_time = perf_counter() - start
            absolute_error = np.abs(target["delay_avg_ns"].to_numpy(dtype=float) - prediction)
            rho = spearmanr(target["delay_avg_ns"].to_numpy(dtype=float), prediction).statistic
            pool_rows.append(
                {
                    "pdk": pdk,
                    "cohort": decision.cohort,
                    "seed": int(decision.seed),
                    "heldout_corner": decision.heldout_corner,
                    "evaluation_stage": evaluation_stage,
                    "support_budget": budget,
                    "delay_r2": float(r2_score(target["delay_avg_ns"], prediction)),
                    "delay_mae_ns": float(mean_absolute_error(target["delay_avg_ns"], prediction)),
                    "delay_p95_absolute_error_ns": float(np.quantile(absolute_error, 0.95)),
                    "delay_max_absolute_error_ns": float(absolute_error.max()),
                    "spearman_rho": float(rho),
                    "top20_slowest_recall": float(
                        top_fraction_recall(target["delay_avg_ns"].to_numpy(dtype=float), prediction)
                    ),
                    "model_fit_time_s": fit_time,
                    "model_predict_time_s": predict_time,
                }
            )
            for variant, group in target.assign(prediction=prediction).groupby("cell_variant", sort=True):
                actual = group["delay_avg_ns"].to_numpy(dtype=float)
                predicted = group["prediction"].to_numpy(dtype=float)
                errors = np.abs(actual - predicted)
                variant_rows.append(
                    {
                        "pdk": pdk,
                        "cohort": decision.cohort,
                        "seed": int(decision.seed),
                        "heldout_corner": decision.heldout_corner,
                        "evaluation_stage": evaluation_stage,
                        "support_budget": budget,
                        "cell_family": str(group["cell_family"].iloc[0]),
                        "cell_variant": str(variant),
                        "points": int(len(group)),
                        "target_delay_std_ns": float(np.std(actual, ddof=1)),
                        "target_delay_iqr_ns": float(np.quantile(actual, 0.75) - np.quantile(actual, 0.25)),
                        "delay_r2": float(r2_score(actual, predicted)),
                        "delay_mae_ns": float(mean_absolute_error(actual, predicted)),
                        "delay_nmae": float(mean_absolute_error(actual, predicted) / robust_scale(pd.Series(actual))),
                        "delay_p95_absolute_error_ns": float(np.quantile(errors, 0.95)),
                        "delay_max_absolute_error_ns": float(errors.max()),
                    }
                )
    return pd.DataFrame(variant_rows), pd.DataFrame(pool_rows)


def threshold_grid(gf_development: pd.DataFrame, gf_confirmation: pd.DataFrame, sky: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for minimum, preq, change, coverage in product(
        [16, 32, 48, 64],
        [0.15, 0.25, 0.40, 0.60, 1.00],
        [0.02, 0.05, 0.10, 0.20, 0.40],
        [0.35, 0.50, 0.65, 0.80],
    ):
        rule = {
            "minimum_budget": minimum,
            "prequential_nmae_threshold": preq,
            "prediction_change_threshold": change,
            "coverage_ratio_threshold": coverage,
        }
        for pdk, cohort, trajectory in (
            ("GF180MCU", "development", gf_development),
            ("GF180MCU", "confirmation", gf_confirmation),
            ("SKY130", "external_replication", sky),
        ):
            decisions = decision_rows(
                trajectory,
                pdk,
                cohort,
                "three_signal_rule",
                ("prequential", "prediction_change", "coverage"),
                rule=rule,
            )
            rows.append(
                {
                    "pdk": pdk,
                    "cohort": cohort,
                    **rule,
                    "median_stop_budget": float(decisions["stop_budget"].median()),
                    "early_stop_runs": int(decisions["early_stopped"].sum()),
                    "gap_le_0p02_rate": float(decisions["gap_le_0p02"].mean()),
                    "maximum_gap_to_full": float(decisions["delay_r2_gap_to_full"].max()),
                    "meets_development_constraints": bool(
                        cohort == "development"
                        and decisions["gap_le_0p02"].mean() >= 8 / 9
                        and decisions["delay_r2_gap_to_full"].max() <= 0.05
                    ),
                }
            )
    return pd.DataFrame(rows)


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    gf_trajectory = pd.read_csv(GF_ROOT / "online" / "library_online_trajectory.csv")
    sky_trajectory = pd.read_csv(SKY_ROOT / "online" / "sky130_online_trajectory.csv")
    gf_development = gf_trajectory[gf_trajectory["seed"].isin([0, 1, 2])].copy()
    gf_confirmation = gf_trajectory[gf_trajectory["seed"].isin([3, 4])].copy()

    signal_sets = {
        "prequential_only": ("prequential",),
        "prediction_change_only": ("prediction_change",),
        "coverage_only": ("coverage",),
        "prequential_plus_prediction_change": ("prequential", "prediction_change"),
        "prequential_plus_coverage": ("prequential", "coverage"),
        "prediction_change_plus_coverage": ("prediction_change", "coverage"),
        "locked_three_signal_rule": ("prequential", "prediction_change", "coverage"),
    }
    decision_frames: list[pd.DataFrame] = []
    for pdk, cohort, trajectory in (
        ("GF180MCU", "confirmation", gf_confirmation),
        ("SKY130", "external_replication", sky_trajectory),
    ):
        for method, signals in signal_sets.items():
            decision_frames.append(decision_rows(trajectory, pdk, cohort, method, signals))
        for budget in (48, 64, 80, 96):
            decision_frames.append(
                decision_rows(trajectory, pdk, cohort, f"fixed_{budget}", fixed_budget=budget)
            )
    all_decisions = pd.concat(decision_frames, ignore_index=True)
    all_decisions.to_csv(OUTDIR / "stopping_rule_ablation_decisions.csv", index=False)

    ablation_summary = []
    for _, group in all_decisions.groupby(["pdk", "cohort", "method"], sort=True):
        ablation_summary.extend(
            summarize_decisions(group, subset)
            for subset in ("all_runs", "early_stop_only", "full_budget_fallback")
        )
    pd.DataFrame(ablation_summary).to_csv(OUTDIR / "stopping_rule_ablation_summary.csv", index=False)

    locked = all_decisions[all_decisions["method"].eq("locked_three_signal_rule")].copy()
    locked.to_csv(OUTDIR / "fixed_seed_locked_decisions.csv", index=False)
    conditional = []
    for _, group in locked.groupby(["pdk", "cohort"], sort=True):
        conditional.extend(
            summarize_decisions(group, subset)
            for subset in ("all_runs", "early_stop_only", "full_budget_fallback")
        )
    conditional_frame = pd.DataFrame(conditional)
    conditional_frame.to_csv(OUTDIR / "conditional_stopping_summary.csv", index=False)

    gf_primary = load_gf_dataset(GF_ROOT / "primary" / "library_primary.csv")
    gf_validation = load_gf_dataset(GF_ROOT / "validation" / "library_validation.csv")
    sky_primary = load_sky_dataset(SKY_ROOT / "primary" / "sky130_library_primary.csv")
    sky_validation = load_sky_dataset(SKY_ROOT / "validation" / "sky130_library_validation.csv")
    gf_variants, gf_pools = evaluate_selected_budgets(
        "GF180MCU",
        gf_primary,
        gf_validation,
        locked[locked["pdk"].eq("GF180MCU")],
        GF_ROOT / "online",
    )
    sky_variants, sky_pools = evaluate_selected_budgets(
        "SKY130",
        sky_primary,
        sky_validation,
        locked[locked["pdk"].eq("SKY130")],
        SKY_ROOT / "online",
    )
    variant_metrics = pd.concat([gf_variants, sky_variants], ignore_index=True)
    pool_metrics = pd.concat([gf_pools, sky_pools], ignore_index=True)
    variant_metrics.to_csv(OUTDIR / "per_variant_delay_metrics.csv", index=False)
    pool_metrics.to_csv(OUTDIR / "pool_tail_and_ranking_metrics.csv", index=False)

    prospective = pd.read_csv(
        PROJECT_ROOT / "results/prospective_locked_confirmation/prospective_confirmation_results.csv"
    )
    prospective["cohort"] = "prospective_seed_5"
    prospective = prospective.rename(columns={"decision_budget": "stop_budget"})
    prospective_gf_variants, prospective_gf_pools = evaluate_selected_budgets(
        "GF180MCU",
        gf_primary,
        gf_validation,
        prospective[prospective["pdk"].eq("GF180MCU")],
        PROJECT_ROOT / "results/prospective_locked_confirmation/gf180",
        measurement_filename="sequential_measurements.csv",
        runs_subdir="",
    )
    prospective_sky_variants, prospective_sky_pools = evaluate_selected_budgets(
        "SKY130",
        sky_primary,
        sky_validation,
        prospective[prospective["pdk"].eq("SKY130")],
        PROJECT_ROOT / "results/prospective_locked_confirmation/sky130",
        measurement_filename="sequential_measurements.csv",
        runs_subdir="",
    )
    prospective_variant_metrics = pd.concat(
        [prospective_gf_variants, prospective_sky_variants], ignore_index=True
    )
    prospective_pool_metrics = pd.concat(
        [prospective_gf_pools, prospective_sky_pools], ignore_index=True
    )
    prospective_variant_metrics.to_csv(
        OUTDIR / "prospective_per_variant_delay_metrics.csv", index=False
    )
    prospective_pool_metrics.to_csv(
        OUTDIR / "prospective_pool_tail_and_ranking_metrics.csv", index=False
    )

    cost_rows = []
    for pdk, group in locked.groupby("pdk", sort=True):
        pool_group = pool_metrics[pool_metrics["pdk"].eq(pdk)]
        stopped_models = pool_group[pool_group["evaluation_stage"].eq("stopped")]
        for subset, data in (
            ("all_runs", group),
            ("early_stop_only", group[group["early_stopped"]]),
            ("full_budget_fallback", group[~group["early_stopped"]]),
        ):
            cost_rows.append(
                {
                    "pdk": pdk,
                    "subset": subset,
                    "runs": int(len(data)),
                    "spice_calls_used": int(data["stop_budget"].sum()),
                    "spice_calls_full_reference": int(96 * len(data)),
                    "spice_calls_avoided_at_decision": int((96 - data["stop_budget"]).sum()),
                    "cumulative_per_call_spice_time_used_s": float(data["cumulative_spice_wall_time_s"].sum()),
                    "cumulative_per_call_spice_time_full_s": float(data["full_cumulative_spice_wall_time_s"].sum()),
                    "median_model_fit_time_s": float(stopped_models["model_fit_time_s"].median()),
                    "median_model_predict_time_s": float(stopped_models["model_predict_time_s"].median()),
                }
            )
    pd.DataFrame(cost_rows).to_csv(OUTDIR / "cost_ledger.csv", index=False)

    sensitivity = threshold_grid(gf_development, gf_confirmation, sky_trajectory)
    sensitivity.to_csv(OUTDIR / "threshold_grid_sensitivity.csv", index=False)
    dev_grid = sensitivity[sensitivity["cohort"].eq("development")]
    eligible_rules = int(dev_grid["meets_development_constraints"].sum())

    stopped_variants = variant_metrics[variant_metrics["evaluation_stage"].eq("stopped")]
    range_error_rho = {}
    for pdk, group in stopped_variants.groupby("pdk"):
        range_error_rho[pdk] = float(
            spearmanr(group["target_delay_std_ns"], group["delay_r2"], nan_policy="omit").statistic
        )
    audit = {
        "fixed_estimator_random_state": True,
        "locked_rule_unchanged_after_correction": EXPECTED_LOCKED_RULE,
        "conditional_stopping": conditional_frame.to_dict(orient="records"),
        "development_grid_rules": int(len(dev_grid)),
        "development_rules_meeting_prespecified_constraints": eligible_rules,
        "spearman_target_std_vs_variant_r2_at_stop": range_error_rho,
        "interpretation_limits": [
            "Exact binomial intervals are descriptive because corner pools sharing a seed and PDK are not fully independent.",
            "Cumulative SPICE time is the sum of per-call engine times, not elapsed time under parallel execution.",
            "Negative per-variant R2 can coexist with modest absolute error when a variant has a narrow delay range.",
            "Released-pool analyses replay stopping over completed measured pools; prospective confirmation is reported separately.",
        ],
    }
    (OUTDIR / "revision_risk_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    report = [
        "# Revision-risk audit",
        "",
        "Estimator randomness is fixed to the pool seed at every support budget. "
        "The previously locked three-signal rule remains unchanged.",
        "",
        "## Conditional stopping result",
        "",
        "```text",
        conditional_frame.to_string(index=False),
        "```",
        "",
        f"The GF180MCU development grid contained {len(dev_grid)} rules; {eligible_rules} met the "
        "prespecified development constraints. This is a sensitivity count, not additional confirmation evidence.",
        "",
        "## Interpretation limits",
        "",
        *[f"- {item}" for item in audit["interpretation_limits"]],
    ]
    (OUTDIR / "revision_risk_audit.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
