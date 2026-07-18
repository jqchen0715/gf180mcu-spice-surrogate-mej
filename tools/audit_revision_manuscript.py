#!/usr/bin/env python3
"""Audit the rebuilt manuscript against fixed-seed and prospective outputs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "manuscript/mej_deterministic_online_submission.tex"
REPORT = ROOT / "manuscript/mej_revision_risk_numeric_audit.md"


def close(name: str, actual: float, expected: float, tolerance: float = 5e-4) -> str:
    if not np.isclose(actual, expected, atol=tolerance, rtol=0):
        raise AssertionError(f"{name}: expected {expected}, found {actual}")
    return f"- PASS: {name} = {actual:.6g}."


def require(text: str, token: str, name: str) -> str:
    if token not in text:
        raise AssertionError(f"{name}: missing manuscript token {token!r}")
    return f"- PASS: {name} appears as `{token}`."


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    text = MANUSCRIPT.read_text(encoding="utf-8")
    audit_root = ROOT / "results/revision_risk_audit"
    prospective_root = ROOT / "results/prospective_locked_confirmation"
    conditional = pd.read_csv(audit_root / "conditional_stopping_summary.csv")
    tails = pd.read_csv(audit_root / "pool_tail_and_ranking_metrics.csv")
    prospective_tails = pd.read_csv(audit_root / "prospective_pool_tail_and_ranking_metrics.csv")
    prospective = pd.read_csv(prospective_root / "prospective_confirmation_results.csv")
    sensitivity = pd.read_csv(audit_root / "threshold_grid_sensitivity.csv")

    lines = ["# Rebuilt Manuscript Numeric Audit", ""]
    gf_all = conditional[(conditional["pdk"] == "GF180MCU") & (conditional["subset"] == "all_runs")].iloc[0]
    gf_early = conditional[(conditional["pdk"] == "GF180MCU") & (conditional["subset"] == "early_stop_only")].iloc[0]
    sky_all = conditional[(conditional["pdk"] == "SKY130") & (conditional["subset"] == "all_runs")].iloc[0]
    sky_early = conditional[(conditional["pdk"] == "SKY130") & (conditional["subset"] == "early_stop_only")].iloc[0]
    for name, actual, expected in (
        ("GF confirmation success rate", gf_all["gap_le_0p02_rate"], 5 / 6),
        ("GF early-stop success rate", gf_early["gap_le_0p02_rate"], 2 / 3),
        ("SKY130 completed-pool success rate", sky_all["gap_le_0p02_rate"], 1.0),
        ("SKY130 early-stop success rate", sky_early["gap_le_0p02_rate"], 1.0),
        ("GF exact lower interval", gf_all["exact_95ci_lower"], 0.3588),
        ("SKY130 exact lower interval", sky_all["exact_95ci_lower"], 0.7820),
    ):
        lines.append(close(name, float(actual), expected))

    if len(prospective) != 6 or not prospective["gap_le_0p02"].all():
        raise AssertionError("Prospective cohort is not six successful pools")
    if int((prospective["decision_budget"] < 96).sum()) != 4:
        raise AssertionError("Prospective early-stop count changed")
    lines.append("- PASS: prospective confirmation contains six successful pools, four 80-call stops, and two 96-call fallbacks.")
    lines.append(close("prospective maximum gap", prospective["delay_r2_gap_to_full"].max(), 0.0190))

    decision_files = sorted(prospective_root.glob("*/seed_5/corner_*/decision_record.json"))
    if len(decision_files) != 6:
        raise AssertionError("Expected six decision records")
    for decision_path in decision_files:
        decision = json.loads(decision_path.read_text(encoding="utf-8"))
        snapshot = decision_path.parent / "decision_snapshot.csv"
        snapshot_rows = len(pd.read_csv(snapshot))
        if file_sha256(snapshot) != decision["decision_snapshot_sha256"]:
            raise AssertionError(f"Decision snapshot hash changed: {snapshot}")
        if snapshot_rows != int(decision["decision_budget"]):
            raise AssertionError(f"Decision snapshot row count changed: {snapshot}")
        if decision["validation_labels_opened_before_decision"] is not False:
            raise AssertionError(f"Validation visibility flag changed: {decision_path}")
    lines.append("- PASS: all six decision-snapshot hashes, row counts, and validation-visibility flags revalidate.")

    completed_stopped = tails[tails["evaluation_stage"].eq("stopped")]
    prospective_stopped = prospective_tails[prospective_tails["evaluation_stage"].eq("stopped")]
    expected_tail = {
        ("GF180MCU", "completed", "delay_mae_ns"): 0.5401,
        ("GF180MCU", "completed", "delay_p95_absolute_error_ns"): 1.7026,
        ("SKY130", "completed", "delay_mae_ns"): 0.2099,
        ("SKY130", "completed", "delay_p95_absolute_error_ns"): 0.5785,
        ("GF180MCU", "prospective", "delay_p95_absolute_error_ns"): 1.7957,
        ("SKY130", "prospective", "delay_p95_absolute_error_ns"): 0.5789,
    }
    for (pdk, cohort, metric), expected in expected_tail.items():
        source = completed_stopped if cohort == "completed" else prospective_stopped
        actual = source[source["pdk"].eq(pdk)][metric].median()
        lines.append(close(f"{pdk} {cohort} median {metric}", float(actual), expected))

    development = sensitivity[sensitivity["cohort"].eq("development")]
    if len(development) != 400 or int(development["meets_development_constraints"].sum()) != 238:
        raise AssertionError("Threshold-grid sensitivity count changed")
    lines.append("- PASS: 238 of 400 development-grid rules meet the prespecified constraints.")

    completion_files = sorted(
        (ROOT / "results/online_spice_deterministic/exhaustive_reference").glob(
            "seed_*/corner_*/completion_queries.csv"
        )
    )
    controlled_completion = sum(len(pd.read_csv(path)) for path in completion_files)
    component_counts = {
        "controlled_primary": len(pd.read_csv(ROOT / "data/dataset_primary_deterministic_320.csv")),
        "controlled_validation": len(pd.read_csv(ROOT / "data/dataset_validation_deterministic_480.csv")),
        "controlled_online": len(pd.read_csv(ROOT / "results/online_spice_deterministic/online_spice_queries.csv")),
        "controlled_completion": controlled_completion,
        "gf_primary": len(pd.read_csv(ROOT / "results/gf180_library_external_validation/primary/library_primary.csv")),
        "gf_validation": len(pd.read_csv(ROOT / "results/gf180_library_external_validation/validation/library_validation.csv")),
        "gf_online": sum(
            len(pd.read_csv(path))
            for path in (ROOT / "results/gf180_library_external_validation/online/runs").glob(
                "seed_*/corner_*/measured_pool_96.csv"
            )
        ),
        "gf_liberty": len(
            pd.read_csv(
                ROOT / "results/gf180_library_external_validation/liberty_crosscheck/liberty_spice_point_comparison.csv"
            )
        ),
        "sky_primary": len(pd.read_csv(ROOT / "results/sky130_cross_pdk_replication/primary/sky130_library_primary.csv")),
        "sky_validation": len(pd.read_csv(ROOT / "results/sky130_cross_pdk_replication/validation/sky130_library_validation.csv")),
        "sky_online": sum(
            len(pd.read_csv(path))
            for path in (ROOT / "results/sky130_cross_pdk_replication/online/runs").glob(
                "seed_*/corner_*/measured_pool_96.csv"
            )
        ),
        "prospective": sum(
            len(pd.read_csv(path))
            for path in prospective_root.glob("*/seed_5/corner_*/sequential_measurements.csv")
        ),
    }
    if sum(component_counts.values()) != 10669:
        raise AssertionError(f"Evidence call total changed: {component_counts}")
    lines.append(f"- PASS: component-level call counts sum to 10,669: `{component_counts}`.")

    for token, name in (
        ("A Validation-Blind Simulator-in-the-Loop Stopping Protocol", "reframed title"),
        ("2/3 and 8/8", "conditional early-stop results"),
        ("maximum gap 0.0190", "prospective maximum gap"),
        ("10,669-call", "complete call count"),
        ("238 meet", "threshold-grid count"),
        ("$R^2=-0.512$", "GF worst-variant disclosure"),
        ("$-4.04$", "SKY130 narrow-range failure disclosure"),
    ):
        lines.append(require(text, token, name))

    model_source = (ROOT / "experiments/library_online_external_validation.py").read_text(encoding="utf-8")
    if "fit_delay(train, seed, n_estimators)" not in model_source or "budget * 17" in model_source:
        raise AssertionError("Estimator random state is not fixed across budgets")
    lines.append("- PASS: estimator random state is fixed to the pool seed across support budgets.")

    pdf = ROOT / "manuscript/mej_deterministic_online_submission.pdf"
    if not pdf.exists() or pdf.stat().st_size < 100000:
        raise AssertionError("Compiled manuscript PDF is missing or unexpectedly small")
    lines.append(f"- PASS: compiled manuscript PDF exists ({pdf.stat().st_size} bytes).")

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
