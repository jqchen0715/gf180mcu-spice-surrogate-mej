#!/usr/bin/env python3
"""Plot few-shot transfer curves for the primary GF180MCU SPICE dataset."""

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
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS = PROJECT_ROOT / "results" / "v2" / "v2_baseline_transfer_results.csv"
DEFAULT_OUTDIR = PROJECT_ROOT / "results" / "v2"
TARGET_LABELS = {
    "delay_avg_ns": "Average delay",
    "power_avg_uW": "Average power",
}


def best_by_protocol(results: pd.DataFrame, experiment: str) -> pd.DataFrame:
    df = results[results["experiment"] == experiment].copy()
    df["fewshot_k"] = pd.to_numeric(df["fewshot_k"], errors="coerce").astype(int)
    return (
        df.sort_values(
            ["target", "heldout_cell", "fewshot_k", "r2"],
            ascending=[True, True, True, False],
        )
        .groupby(["target", "heldout_cell", "fewshot_k"])
        .head(1)
    )


def summarize(best: pd.DataFrame, label: str) -> pd.DataFrame:
    summary = (
        best.groupby(["target", "fewshot_k"])
        .agg(
            median_r2=("r2", "median"),
            min_r2=("r2", "min"),
            median_mae=("mae", "median"),
        )
        .reset_index()
    )
    summary["protocol"] = label
    return summary


def main() -> int:
    results = pd.read_csv(DEFAULT_RESULTS)
    transfer = summarize(best_by_protocol(results, "cell_transfer"), "Transfer")
    scratch = summarize(best_by_protocol(results, "cell_fewshot_from_scratch"), "From scratch")
    combined = pd.concat([transfer, scratch], ignore_index=True)
    combined = combined[combined["fewshot_k"] > 0].copy()

    fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharex=True)
    colors = {"Transfer": "#1f77b4", "From scratch": "#d62728"}
    markers = {"Transfer": "o", "From scratch": "s"}

    for col, target in enumerate(["delay_avg_ns", "power_avg_uW"]):
        target_df = combined[combined["target"] == target]
        for protocol, proto_df in target_df.groupby("protocol"):
            proto_df = proto_df.sort_values("fewshot_k")
            axes[0, col].plot(
                proto_df["fewshot_k"],
                proto_df["median_r2"],
                marker=markers[protocol],
                color=colors[protocol],
                linewidth=2,
                label=protocol,
            )
            axes[1, col].plot(
                proto_df["fewshot_k"],
                proto_df["median_mae"],
                marker=markers[protocol],
                color=colors[protocol],
                linewidth=2,
                label=protocol,
            )

        axes[0, col].set_title(TARGET_LABELS[target])
        axes[0, col].set_ylabel(r"Median $R^2$")
        axes[1, col].set_ylabel("Median MAE")
        axes[1, col].set_xlabel("Target-cell support samples (k)")
        axes[0, col].grid(True, alpha=0.25)
        axes[1, col].grid(True, alpha=0.25)
        axes[0, col].set_xticks([5, 10, 20, 40])
        axes[1, col].set_xticks([5, 10, 20, 40])

    axes[0, 0].legend(frameon=False, loc="lower right")
    fig.suptitle("Few-shot cross-cell transfer on held-out target cells")
    fig.tight_layout()

    DEFAULT_OUTDIR.mkdir(parents=True, exist_ok=True)
    png = DEFAULT_OUTDIR / "v2_fewshot_transfer_curves.png"
    pdf = DEFAULT_OUTDIR / "v2_fewshot_transfer_curves.pdf"
    fig.savefig(png, dpi=300, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    print(f"Wrote {png}")
    print(f"Wrote {pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
