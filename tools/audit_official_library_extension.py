#!/usr/bin/env python3
"""Audit the released-CDL extension against manuscript claims."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "gf180_library_external_validation"
ONLINE = RESULTS / "online"
MANUSCRIPT = ROOT / "manuscript" / "mej_deterministic_online_submission.tex"
REPORT_DIR = ROOT / ("manuscript_audits" if (ROOT / "manuscript_audits").is_dir() else "manuscript")
REPORT = REPORT_DIR / "mej_official_library_extension_numeric_audit.md"


def close(name: str, actual: float, expected: float, tolerance: float = 5e-5) -> str:
    if not np.isclose(actual, expected, atol=tolerance, rtol=0):
        raise AssertionError(f"{name}: expected {expected}, found {actual}")
    return f"- PASS: {name} = {actual:.6g}."


def token(text: str, value: str, name: str) -> str:
    if value not in text:
        raise AssertionError(f"{name}: manuscript token not found: {value}")
    return f"- PASS: {name} is reported as `{value}`."


def main() -> int:
    text = MANUSCRIPT.read_text(encoding="utf-8")
    primary = pd.read_csv(RESULTS / "primary" / "library_primary.csv")
    validation = pd.read_csv(RESULTS / "validation" / "library_validation.csv")
    pooled = pd.read_csv(ONLINE / "library_online_pooled_summary.csv").set_index("support_budget")
    stopping = pd.read_csv(ONLINE / "stopping" / "stopping_confirmation_summary.csv").set_index("method")
    liberty = pd.read_csv(RESULTS / "liberty_crosscheck" / "liberty_spice_agreement_metrics.csv")
    liberty_all = liberty[(liberty["group"] == "all") & (liberty["value"] == "all")].iloc[0]

    lines = ["# Official-Library Extension Numeric Audit", ""]
    for name, frame in (("primary", primary), ("validation", validation)):
        if len(frame) != 576 or not frame["status"].eq("ok").all():
            raise AssertionError(f"{name} dataset row count or status changed")
        if set(frame["statistical_mode"]) != {"off"}:
            raise AssertionError(f"{name} dataset is not deterministic")
        if frame["cell_family"].nunique() != 8 or frame["cell_variant"].nunique() != 16:
            raise AssertionError(f"{name} library coverage changed")
        if set(frame["drive_strength"].astype(int)) != {1, 4}:
            raise AssertionError(f"{name} drive strengths changed")
    lines.append("- PASS: both independent released-CDL datasets contain 576 successful deterministic rows, eight families, 16 variants, and drive strengths 1/4.")

    pool_files = sorted((ONLINE / "runs").glob("seed_*/corner_*/measured_pool_96.csv"))
    measured = pd.concat([pd.read_csv(path) for path in pool_files], ignore_index=True)
    if len(pool_files) != 15 or len(measured) != 1440 or not measured["status"].eq("ok").all():
        raise AssertionError("Measured online pool count, row count, or status changed")
    lines.append("- PASS: 15 measured pools contain 1440 successful fresh SPICE calls.")

    for budget, expected in {0: 0.2171, 32: 0.8217, 48: 0.8633, 80: 0.8967, 96: 0.9097}.items():
        lines.append(close(f"released-CDL median delay R2 at budget {budget}", pooled.loc[budget, "median_delay_r2"], expected))
    lines.append(close("released-CDL median worst-family R2 at budget 48", pooled.loc[48, "median_worst_family_r2"], 0.3722))
    lines.append(close("released-CDL median worst-family R2 at budget 96", pooled.loc[96, "median_worst_family_r2"], 0.7196))

    locked = stopping.loc["locked_rule"]
    lines.append(close("confirmation median stop budget", locked["median_stop_budget"], 88.0))
    lines.append(close("confirmation maximum gap", locked["maximum_delay_r2_gap_to_full"], 0.0226))
    lines.append(close("confirmation gap <= 0.02 rate", locked["gap_le_0p02_rate"], 5 / 6))
    lines.append(close("confirmation gap <= 0.05 rate", locked["gap_le_0p05_rate"], 1.0))
    lines.append(close("confirmation median worst-family R2", locked["median_worst_family_delay_r2"], 0.7389))

    if int(liberty_all["points"]) != 432:
        raise AssertionError("Liberty point count changed")
    lines.append(close("Liberty Spearman rho", liberty_all["spearman_rho"], 0.9900))
    lines.append(close("Liberty Pearson r", liberty_all["pearson_r"], 0.9916))
    lines.append(close("Liberty R2", liberty_all["r2"], 0.9460))
    lines.append(close("Liberty median absolute percentage error", liberty_all["median_absolute_percentage_error"], 18.58, tolerance=0.01))
    lines.append(close("Liberty median SPICE-to-Liberty ratio", liberty_all["median_spice_to_liberty_ratio"], 0.814, tolerance=5e-4))

    for value, name in [
        ("1440", "online call count"),
        ("0.2171", "zero-support external result"),
        ("0.8633", "48-query external result"),
        ("0.9097", "full external result"),
        ("0.0226", "maximum stopping gap"),
        ("0.7389", "stopped worst-family result"),
        ("0.9900", "Liberty rank correlation"),
        ("18.58\\%", "Liberty absolute-error boundary"),
    ]:
        lines.append(token(text, value, name))

    figure = ROOT / "manuscript" / "figures" / "fig3_official_library_validation.pdf"
    if not figure.exists() or figure.stat().st_size == 0:
        raise AssertionError("Official-library figure is missing")
    lines.append("- PASS: the released-library validation figure exists.")

    public_tables = [primary, validation, measured]
    if any(frame.astype(str).apply(lambda col: col.str.contains("/Users/", regex=False).any()).any() for frame in public_tables):
        raise AssertionError("An absolute user path remains in released-library CSV data")
    lines.append("- PASS: released-library CSV data contain no absolute `/Users/` paths.")

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {REPORT}")
    print("All official-library extension checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
