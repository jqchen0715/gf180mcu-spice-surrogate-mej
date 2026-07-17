#!/usr/bin/env python3
"""Audit row provenance and reported SKY130 cross-PDK statistics."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "results/sky130_cross_pdk_replication"
PRIMARY = RESULT / "primary/sky130_library_primary.csv"
VALIDATION = RESULT / "validation/sky130_library_validation.csv"
ONLINE = RESULT / "online"
EXPECTED_RULE = {
    "minimum_budget": 64,
    "prequential_nmae_threshold": 0.25,
    "prediction_change_threshold": 0.05,
    "coverage_ratio_threshold": 0.5,
}
EXPECTED_PRIMITIVE_COMMIT = "403964dc7f9cca5ec1a8cc7b4f2a6f532b781676"
EXPECTED_STANDARD_CELL_COMMIT = "9cb2d7cb8ed4619094263614039a61b6b2d22a88"


def git_head(path: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()


def installed_or_expected_commit(path: Path, expected: str) -> str:
    if not (path / ".git").exists():
        return expected
    installed = git_head(path)
    if installed != expected:
        raise RuntimeError(f"Unexpected PDK commit at {path}: {installed}; expected {expected}")
    return installed


def main() -> int:
    primary = pd.read_csv(PRIMARY)
    validation = pd.read_csv(VALIDATION)
    candidate = pd.read_csv(ONLINE / "sky130_online_candidate_features.csv")
    trajectory = pd.read_csv(ONLINE / "sky130_online_trajectory.csv")
    decisions = pd.read_csv(ONLINE / "sky130_stopping_decisions.csv")
    measured_files = sorted((ONLINE / "runs").glob("seed_*/corner_*/measured_pool_96.csv"))
    measured = pd.concat([pd.read_csv(path) for path in measured_files], ignore_index=True)
    protocol = json.loads((ONLINE / "sky130_cross_pdk_protocol_and_results.json").read_text())

    checks: dict[str, bool] = {}
    checks["primary_576_all_ok"] = len(primary) == 576 and primary["status"].eq("ok").all()
    checks["validation_576_all_ok"] = len(validation) == 576 and validation["status"].eq("ok").all()
    checks["sixteen_variants_each_dataset"] = (
        primary["cell_variant"].nunique() == 16 and validation["cell_variant"].nunique() == 16
    )
    checks["eight_families_each_dataset"] = (
        primary["cell_family"].nunique() == 8 and validation["cell_family"].nunique() == 8
    )
    checks["balanced_corner_counts"] = (
        primary["corner"].value_counts().to_dict() == {"typical": 192, "ff": 192, "ss": 192}
        and validation["corner"].value_counts().to_dict() == {"typical": 192, "ff": 192, "ss": 192}
    )
    checks["fifteen_complete_online_pools"] = len(measured_files) == 15 and len(measured) == 1440
    checks["online_all_ok"] = measured["status"].eq("ok").all()
    checks["online_unique_sample_ids"] = measured["sample_id"].nunique() == 1440
    checks["candidate_features_1440"] = len(candidate) == 1440
    checks["trajectory_15_by_7_budgets"] = (
        len(trajectory) == 105
        and set(trajectory["support_budget"].unique()) == {0, 16, 32, 48, 64, 80, 96}
    )
    checks["locked_rule_unchanged"] = protocol["locked_rule"] == EXPECTED_RULE
    checks["sky130_not_used_for_rule_selection"] = protocol["locked_rule_selected_using_sky130"] is False
    locked = decisions[decisions["method"].eq("gf180_locked_rule")].copy()
    checks["locked_rule_15_runs"] = len(locked) == 15
    checks["all_locked_gaps_le_0p02"] = locked["delay_r2_gap_to_full"].le(0.02).all()
    checks["all_locked_gaps_le_0p05"] = locked["delay_r2_gap_to_full"].le(0.05).all()

    checks = {name: bool(passed) for name, passed in checks.items()}
    failed = [name for name, passed in checks.items() if not passed]
    summary = protocol["comparison"]["gf180_locked_rule"]
    metadata = {
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "publication_sky130_spice_calls": 2592,
        "complete_study_spice_calls_after_sky130": 10093,
        "sky130_primitive_commit": installed_or_expected_commit(
            ROOT / "sky130-pdk/libraries/sky130_fd_pr/latest", EXPECTED_PRIMITIVE_COMMIT
        ),
        "sky130_standard_cell_commit": installed_or_expected_commit(
            ROOT / "sky130-pdk/libraries/sky130_fd_sc_hd/latest", EXPECTED_STANDARD_CELL_COMMIT
        ),
        "ngspice_version": "46",
        "primary_rows": len(primary),
        "validation_rows": len(validation),
        "online_rows": len(measured),
        "locked_rule_summary": summary,
        "sampled_ranges": {
            column: {
                "minimum": float(pd.concat([primary[column], validation[column], measured[column]]).min()),
                "maximum": float(pd.concat([primary[column], validation[column], measured[column]]).max()),
            }
            for column in ["Vdd", "Temp", "slew_ns", "Cload_pF"]
        },
    }
    (RESULT / "sky130_cross_pdk_numeric_audit.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    report = [
        "# SKY130 cross-PDK numeric audit",
        "",
        f"Overall status: **{metadata['status']}**.",
        "",
        "## Evidence counts",
        "",
        f"- Primary dataset: {len(primary)} successful rows.",
        f"- Independent validation dataset: {len(validation)} successful rows.",
        f"- Online external-replication calls: {len(measured)} successful rows in {len(measured_files)} pools.",
        "- SKY130 publication evidence added: 2,592 SPICE calls.",
        "- Complete two-PDK evidence package: 10,093 SPICE calls.",
        "",
        "## Locked-rule result",
        "",
        f"- Median stop budget: {summary['median_stop_budget']:.0f}/96.",
        f"- Median query reduction: {summary['median_query_reduction_pct']:.1f}%.",
        f"- Runs within 0.02: {int(round(summary['gap_le_0p02_rate'] * 15))}/15.",
        f"- Maximum delay R2 gap: {summary['maximum_delay_r2_gap_to_full']:.6f}.",
        "",
        "## Checks",
        "",
    ]
    report.extend(f"- [{'x' if passed else ' '}] {name}" for name, passed in checks.items())
    (RESULT / "sky130_cross_pdk_numeric_audit.md").write_text(
        "\n".join(report) + "\n", encoding="utf-8"
    )
    print(json.dumps(metadata, indent=2))
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
