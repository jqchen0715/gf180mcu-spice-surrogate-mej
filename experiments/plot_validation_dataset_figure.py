#!/usr/bin/env python3
"""Plot validation-dataset checks for the MEJ manuscript."""

from __future__ import annotations

import os
from pathlib import Path

Path("/private/tmp/matplotlib-cache").mkdir(parents=True, exist_ok=True)
Path("/private/tmp/fontconfig-cache").mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/matplotlib-cache")
os.environ.setdefault("XDG_CACHE_HOME", "/private/tmp/fontconfig-cache")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = PROJECT_ROOT / "results" / "v3_scale_validation"
OUTDIR = PROJECT_ROOT / "manuscript" / "figures"


def clean_model_name(name: str) -> str:
    return {
        "GradientBoosting": "GB",
        "SVR_RBF": "SVR",
        "MLP": "MLP",
    }.get(name, name)


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)

    external = pd.read_csv(RESULT_DIR / "v3_external_validation.csv")
    ranking = pd.read_csv(RESULT_DIR / "v3_external_candidate_ranking_summary.csv")
    support = pd.read_csv(RESULT_DIR / "v3_corner_support_summary.csv")

    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.1))
    colors = {
        "delay_avg_ns": "#2563eb",
        "power_avg_uW": "#dc2626",
        "random": "#94a3b8",
        "surrogate": "#16a34a",
        "ff": "#dc2626",
        "ss": "#7c3aed",
        "typical": "#2563eb",
    }

    # Panel A: direct primary-to-validation prediction.
    ax = axes[0]
    models = ["GradientBoosting", "SVR_RBF", "MLP"]
    x = np.arange(len(models))
    width = 0.36
    for offset, target in [(-width / 2, "delay_avg_ns"), (width / 2, "power_avg_uW")]:
        vals = [
            float(external[(external["model"] == model) & (external["target"] == target)]["r2"].iloc[0])
            for model in models
        ]
        label = "Delay" if target == "delay_avg_ns" else "Power"
        ax.bar(x + offset, vals, width=width, color=colors[target], alpha=0.86, label=label)
    ax.set_xticks(x)
    ax.set_xticklabels([clean_model_name(m) for m in models])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel(r"$R^2$ on validation dataset")
    ax.set_title("Primary-to-validation prediction")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(frameon=False, loc="lower right")

    # Panel B: sampled-pool candidate enrichment.
    ax = axes[1]
    random = ranking[ranking["selection"] == "random_selection"].iloc[0]
    surrogate = ranking[ranking["selection"] != "random_selection"].iloc[0]
    metrics = ["Top-10% hits", "Top-20% hits"]
    random_vals = [random["median_top10_hits"], random["median_top20_hits"]]
    surrogate_vals = [surrogate["median_top10_hits"], surrogate["median_top20_hits"]]
    x = np.arange(len(metrics))
    ax.bar(x - width / 2, random_vals, width=width, color=colors["random"], label="Random median")
    ax.bar(x + width / 2, surrogate_vals, width=width, color=colors["surrogate"], label="Surrogate")
    ax.set_xticks(x)
    ax.set_xticklabels(metrics)
    ax.set_ylim(0, 30)
    ax.set_ylabel("Hits among 24 selected points")
    ax.set_title("Validation candidate enrichment")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(frameon=False, loc="upper left")

    # Panel C: support-calibrated delay extrapolation.
    ax = axes[2]
    delay_support = support[support["target"] == "delay_avg_ns"].copy()
    for corner in ["ff", "ss", "typical"]:
        group = delay_support[delay_support["heldout_corner"] == corner].sort_values("support_rows")
        ax.plot(
            group["support_rows"],
            group["median_r2"],
            marker="o",
            linewidth=2,
            color=colors[corner],
            label=corner,
        )
    ax.set_ylim(0, 1.0)
    ax.set_xlabel("Same-corner support rows")
    ax.set_ylabel(r"Median delay $R^2$")
    ax.set_title("Validation corner-support calibration")
    ax.grid(True, alpha=0.25)
    ax.legend(frameon=False, title="Held-out corner")

    for panel, ax in zip(["A", "B", "C"], axes):
        ax.text(-0.16, 1.08, panel, transform=ax.transAxes, fontsize=12, fontweight="bold", va="top")

    fig.suptitle("Validation-dataset checks for primary-trained surrogate models", fontsize=13, y=1.03)
    fig.tight_layout()

    png = OUTDIR / "fig7_validation_dataset_checks.png"
    pdf = OUTDIR / "fig7_validation_dataset_checks.pdf"
    fig.savefig(png, dpi=300, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    print(f"Wrote {png}")
    print(f"Wrote {pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
