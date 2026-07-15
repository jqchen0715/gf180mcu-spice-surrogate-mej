#!/usr/bin/env python3
"""Audit manuscript claims against deterministic simulator-in-the-loop outputs."""

from __future__ import annotations

from pathlib import Path
import re

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "manuscript" / "mej_deterministic_online_submission.tex"
RESULT_DIR = ROOT / "results" / "online_spice_deterministic"
REPORT_DIR = ROOT / ("manuscript_audits" if (ROOT / "manuscript_audits").is_dir() else "manuscript")
REPORT = REPORT_DIR / "mej_deterministic_online_numeric_audit.md"
PROPOSED = "cell_balanced_space_filling"


def require_close(name: str, actual: float, expected: float, tolerance: float = 5e-5) -> str:
    if not np.isclose(actual, expected, atol=tolerance, rtol=0):
        raise AssertionError(f"{name}: expected {expected}, found {actual}")
    return f"- PASS: {name} = {actual:.6g}."


def require_text(text: str, token: str, name: str) -> str:
    if token not in text:
        raise AssertionError(f"{name}: token not found: {token}")
    return f"- PASS: {name} is present as `{token}`."


def main() -> int:
    text = MANUSCRIPT.read_text(encoding="utf-8")
    primary = pd.read_csv(ROOT / "data" / "dataset_primary_deterministic_320.csv")
    validation = pd.read_csv(ROOT / "data" / "dataset_validation_deterministic_480.csv")
    queries = pd.read_csv(RESULT_DIR / "online_spice_queries.csv")
    trajectory = pd.read_csv(RESULT_DIR / "online_spice_trajectory.csv")
    comparison = pd.read_csv(RESULT_DIR / "online_spice_budget_vs_exhaustive.csv")
    audit = pd.read_csv(RESULT_DIR / "online_spice_duplicate_query_consistency.csv")
    tests = pd.read_csv(RESULT_DIR / "online_spice_paired_tests.csv")
    correlations = pd.read_csv(RESULT_DIR / "online_spice_prequential_correlations.csv")

    lines = ["# Deterministic Online Manuscript Numeric Audit", ""]
    if len(primary) != 320 or len(validation) != 480:
        raise AssertionError("Dataset row counts changed")
    if set(primary["statistical_mode"]) != {"off"} or set(validation["statistical_mode"]) != {"off"}:
        raise AssertionError("Publication datasets are not deterministic")
    if int(primary["sw_stat_global"].max()) != 0 or int(primary["sw_stat_mismatch"].max()) != 0:
        raise AssertionError("Primary statistical switches are not zero")
    lines.append("- PASS: primary/validation row counts are 320/480 and all statistical switches are off.")

    if len(queries) != 3600 or not queries["status"].eq("ok").all():
        raise AssertionError("Online query count or status changed")
    lines.append("- PASS: 3600 online ngspice queries completed successfully.")

    if len(audit) != 1118 or audit["delay_span_ns"].max() != 0 or audit["power_span_uW"].max() != 0:
        raise AssertionError("Repeated-query consistency changed")
    lines.append("- PASS: 1118 repeated candidate groups have zero delay and power spans.")

    proposed = trajectory[trajectory["strategy"] == PROPOSED]
    expected_trajectory = {0: 0.4825, 24: 0.8119, 48: 0.8729}
    for budget, expected in expected_trajectory.items():
        actual = float(proposed[proposed["spice_queries"] == budget]["delay_r2"].median())
        lines.append(require_close(f"proposed median delay R2 at budget {budget}", actual, expected))

    budget48 = comparison[comparison["online_budget"] == 48]
    checks = {
        "48-query reduction percent": (float(budget48["query_reduction_pct"].median()), 50.0),
        "48-query time reduction percent": (float(budget48["measured_time_reduction_pct"].median()), 51.3204),
        "48-query gap to reference": (float(budget48["delay_r2_gap_to_full"].median()), 0.0120),
        "full-reference delay R2": (float(budget48["full_delay_r2"].median()), 0.8824),
        "48-query worst-cell delay R2": (float(budget48["online_worst_cell_delay_r2"].median()), 0.7885),
        "full-reference worst-cell delay R2": (float(budget48["full_worst_cell_delay_r2"].median()), 0.8150),
        "48-query top-20 recall": (float(budget48["online_top20_recall"].median()), 0.9375),
    }
    for name, (actual, expected) in checks.items():
        lines.append(require_close(name, actual, expected))

    p_random = tests[(tests["budget"] == 48) & (tests["metric"] == "delay_r2") & (tests["baseline"] == "random")]["p_holm"].iloc[0]
    p_uncertainty = tests[(tests["budget"] == 48) & (tests["metric"] == "delay_r2") & (tests["baseline"] == "uncertainty")]["p_holm"].iloc[0]
    lines.append(require_close("48-query corrected p versus random", float(p_random), 0.0374))
    lines.append(require_close("48-query corrected p versus uncertainty", float(p_uncertainty), 0.0334))

    rho = correlations[(correlations["internal_metric"] == "prequential_delay_mae_ns") & (correlations["external_metric"] == "external_delay_r2")]["spearman_rho"].iloc[0]
    lines.append(require_close("prequential/external Spearman rho", float(rho), -0.3869))

    for token, name in [
        ("0.4825", "zero-support result"),
        ("0.8119", "24-query result"),
        ("0.8729", "48-query result"),
        ("0.8824", "full-reference result"),
        ("51.3\\%", "measured-time reduction"),
        ("0.0120", "gap to reference"),
        ("p=0.0374", "corrected random comparison"),
        ("p=0.0334", "corrected uncertainty comparison"),
        ("\\journal{Microelectronics Journal}", "journal target"),
    ]:
        lines.append(require_text(text, token, name))

    forbidden = [r"\bV2\b", r"\bV3\b", r"\bV4\b", r"previous paper", r"prior paper"]
    for pattern in forbidden:
        if re.search(pattern, text, flags=re.IGNORECASE):
            raise AssertionError(f"Forbidden legacy wording remains: {pattern}")
    lines.append("- PASS: no V2/V3/V4 or prior-paper wording remains in the manuscript.")

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {REPORT}")
    print("All deterministic online manuscript checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
