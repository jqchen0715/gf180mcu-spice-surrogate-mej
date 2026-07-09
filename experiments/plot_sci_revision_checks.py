#!/usr/bin/env python3
"""Plot the enhanced SCI revision checks as a compact manuscript figure."""

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
RESULT_DIR = PROJECT_ROOT / "results" / "sci_revision"
OUTDIR = PROJECT_ROOT / "manuscript" / "figures"


def short_target(target: str) -> str:
    return "Delay" if target == "delay_avg_ns" else "Power"


def clean_model(name: str) -> str:
    return {
        "GaussianProcess": "GPR",
        "GradientBoosting": "GB",
        "HistGradientBoosting": "HistGB",
        "RandomForest": "RF",
        "ExtraTrees": "ExtraTrees",
        "SVR_RBF": "SVR",
    }.get(name, name)


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)

    external = pd.read_csv(RESULT_DIR / "sci_external_validation_all_models_summary.csv")
    conformal = pd.read_csv(RESULT_DIR / "sci_conformal_intervals_summary.csv")
    importance = pd.read_csv(RESULT_DIR / "sci_permutation_feature_importance.csv")
    model_summary = pd.read_csv(RESULT_DIR / "sci_model_zoo_summary.csv")

    fig, axes = plt.subplots(2, 2, figsize=(11.8, 8.2))
    axes = axes.ravel()
    colors = {"Delay": "#2563eb", "Power": "#dc2626"}

    ax = axes[0]
    top_external = external.groupby("target").head(4).copy()
    targets = ["delay_avg_ns", "power_avg_uW"]
    width = 0.36
    x_base = np.arange(4)
    for idx, target in enumerate(targets):
        group = top_external[top_external["target"] == target].reset_index(drop=True)
        x = x_base + (idx - 0.5) * width
        ax.bar(x, group["r2"], width=width, color=colors[short_target(target)], alpha=0.88, label=short_target(target))
        for xpos, model in zip(x, group["model"]):
            ax.text(xpos, 0.02, clean_model(model), rotation=90, ha="center", va="bottom", fontsize=8, color="white")
    ax.set_ylim(0, 1.05)
    ax.set_xticks(x_base)
    ax.set_xticklabels([f"Rank {i}" for i in range(1, 5)])
    ax.set_ylabel(r"$R^2$ on validation dataset")
    ax.set_title("Primary-to-validation strong baselines")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(frameon=False, loc="lower right")

    ax = axes[1]
    conf = conformal[conformal["experiment"] == "v2_split_conformal"].copy()
    x = np.arange(len(conf))
    bars = ax.bar(
        x,
        conf["median_empirical_coverage"],
        color=[colors[short_target(t)] for t in conf["target"]],
        alpha=0.85,
    )
    ax.axhline(0.90, color="black", linestyle="--", linewidth=1, label="Nominal 90%")
    ax.set_xticks(x)
    ax.set_xticklabels([short_target(t) for t in conf["target"]])
    ax.set_ylim(0.80, 1.00)
    ax.set_ylabel("Empirical coverage")
    ax.set_title("Split conformal intervals")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(frameon=False, loc="lower right")
    for bar, width_value in zip(bars, conf["median_interval_width"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.006, f"w={width_value:.2g}", ha="center", fontsize=8)

    ax = axes[2]
    imp = importance[importance["target"] == "delay_avg_ns"].sort_values("importance_mean_delta_r2", ascending=False).head(6)
    ax.barh(imp["feature"][::-1], imp["importance_mean_delta_r2"][::-1], color="#2563eb", alpha=0.85)
    ax.set_xlabel(r"Permutation importance ($\Delta R^2$)")
    ax.set_title("Delay feature importance")
    ax.grid(True, axis="x", alpha=0.25)

    ax = axes[3]
    delay = model_summary[model_summary["target"] == "delay_avg_ns"].copy()
    power = model_summary[model_summary["target"] == "power_avg_uW"].copy()
    label_offsets = {
        "CatBoost": (0.95, 0.008),
        "GaussianProcess": (1.08, 0.006),
        "XGBoost": (0.96, -0.020),
        "MLP": (1.10, 0.010),
    }
    for df, target_name in [(delay, "Delay"), (power, "Power")]:
        ax.scatter(
            df["median_fit_seconds"],
            df["median_r2"],
            s=55,
            alpha=0.82,
            color=colors[target_name],
            label=target_name,
        )
        for _, row in df.sort_values("median_r2", ascending=False).head(3).iterrows():
            x_scale, y_offset = label_offsets.get(row["model"], (1.0, 0.006))
            ax.text(
                row["median_fit_seconds"] * x_scale,
                row["median_r2"] + y_offset,
                clean_model(row["model"]),
                fontsize=8,
                ha="center",
            )
    ax.set_xscale("log")
    ax.set_xlabel("Median fit time per split (s, log scale)")
    ax.set_ylabel(r"Median random-split $R^2$")
    ax.set_title("Accuracy-cost trade-off")
    ax.grid(True, alpha=0.25)
    ax.legend(frameon=False, loc="lower right")

    for panel, ax in zip(["A", "B", "C", "D"], axes):
        ax.text(-0.13, 1.07, panel, transform=ax.transAxes, fontsize=12, fontweight="bold", va="top")

    fig.suptitle("Enhanced model validation, uncertainty, and cost checks", fontsize=14, y=1.02)
    fig.tight_layout()
    png = OUTDIR / "fig8_sci_revision_checks.png"
    pdf = OUTDIR / "fig8_sci_revision_checks.pdf"
    fig.savefig(png, dpi=300, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    print(f"Wrote {png}")
    print(f"Wrote {pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
