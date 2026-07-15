#!/usr/bin/env python3
"""Plot the deterministic simulator-in-the-loop evidence for the manuscript."""

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
RESULT_DIR = PROJECT_ROOT / "results" / "online_spice_deterministic"
OUTDIR = PROJECT_ROOT / "manuscript" / "figures"

matplotlib.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "font.size": 7,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.linewidth": 0.8,
        "legend.frameon": False,
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
    }
)

METHODS = [
    "random",
    "cell_balanced_random",
    "uncertainty",
    "space_filling",
    "cell_balanced_space_filling",
]
COLORS = {
    "random": "#777777",
    "cell_balanced_random": "#D88A48",
    "uncertainty": "#5C88B3",
    "space_filling": "#4D9B79",
    "cell_balanced_space_filling": "#B45F87",
}
LABELS = {
    "random": "Random",
    "cell_balanced_random": "Cell-balanced random",
    "uncertainty": "Uncertainty",
    "space_filling": "Space-filling",
    "cell_balanced_space_filling": "Cell-balanced space-filling",
}
MARKERS = {
    "random": "o",
    "cell_balanced_random": "s",
    "uncertainty": "^",
    "space_filling": "D",
    "cell_balanced_space_filling": "P",
}


def add_panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(-0.16, 1.08, label, transform=ax.transAxes, fontsize=8, fontweight="bold", va="top")


def draw_corner_panel(ax: plt.Axes, summary: pd.DataFrame, corner: str) -> None:
    corner_data = summary[summary["heldout_corner"] == corner]
    for method in METHODS:
        data = corner_data[corner_data["strategy"] == method].sort_values("spice_queries")
        if data.empty:
            continue
        x = data["spice_queries"].to_numpy(dtype=float)
        y = data["median_delay_r2"].to_numpy(dtype=float)
        lo = data["q25_delay_r2"].to_numpy(dtype=float)
        hi = data["q75_delay_r2"].to_numpy(dtype=float)
        emphasized = method == "cell_balanced_space_filling"
        ax.fill_between(x, lo, hi, color=COLORS[method], alpha=0.10 if emphasized else 0.045, linewidth=0)
        ax.plot(
            x,
            y,
            color=COLORS[method],
            linewidth=1.55 if emphasized else 0.95,
            marker=MARKERS[method],
            markersize=3.4 if emphasized else 2.4,
            markevery=2,
            label=LABELS[method],
            zorder=3 if emphasized else 2,
        )
    ax.axhline(0.75, color="#333333", linestyle=(0, (3, 2)), linewidth=0.8)
    ax.text(49, 0.758, r"$R^2=0.75$", ha="right", va="bottom", fontsize=5.7, color="#333333")
    ax.set_xlim(-1, 49)
    ax.set_ylim(-0.27 if corner == "ff" else 0.15, 0.96)
    ax.set_xticks([0, 12, 24, 36, 48])
    ax.set_title(f"Held-out {corner} corner", fontsize=7.5, pad=4)
    ax.set_xlabel("Same-corner SPICE queries")
    ax.grid(axis="both", color="#d7dce2", linewidth=0.45, alpha=0.7)


def draw_exhaustive_panel(ax: plt.Axes, comparison: pd.DataFrame) -> None:
    labels = ["24 queries", "48 queries", "96-query\nreference"]
    positions = np.arange(3)
    plot_rows = []
    for budget in [24, 48]:
        values = comparison[comparison["online_budget"] == budget]["online_delay_r2"].to_numpy()
        plot_rows.append(values)
    plot_rows.append(
        comparison[comparison["online_budget"] == 48]["full_delay_r2"].to_numpy()
    )
    box = ax.boxplot(
        plot_rows,
        positions=positions,
        widths=0.5,
        patch_artist=True,
        showfliers=False,
        medianprops={"color": "#172033", "linewidth": 1.2},
        whiskerprops={"color": "#64748b", "linewidth": 0.8},
        capprops={"color": "#64748b", "linewidth": 0.8},
    )
    fills = ["#d9bfd0", "#b45f87", "#d8dde4"]
    for patch, fill in zip(box["boxes"], fills):
        patch.set_facecolor(fill)
        patch.set_edgecolor("#64748b")
        patch.set_linewidth(0.8)
    rng = np.random.default_rng(20260715)
    for xpos, values in zip(positions, plot_rows):
        jitter = rng.uniform(-0.075, 0.075, size=len(values))
        ax.scatter(np.full(len(values), xpos) + jitter, values, s=8, color="#334155", alpha=0.52, linewidths=0, zorder=3)
    medians = [float(np.median(values)) for values in plot_rows]
    for xpos, median in zip(positions, medians):
        ax.text(xpos, 0.57, f"{median:.3f}", ha="center", va="bottom", fontsize=6.1)
    ax.text(0, 0.99, "75% fewer queries\n75.7% less measured time", ha="center", va="top", fontsize=6.1, color="#7b365b")
    ax.text(1, 0.99, "50% fewer queries\n51.3% less measured time", ha="center", va="top", fontsize=6.1, color="#7b365b")
    ax.annotate(
        "median gap = 0.012",
        xy=(1.5, 0.873),
        xytext=(1.5, 0.79),
        ha="center",
        fontsize=6,
        arrowprops={"arrowstyle": "-[,widthB=2.2", "lw": 0.75, "color": "#334155"},
    )
    ax.set_xticks(positions, labels)
    ax.set_xlim(-0.55, 2.55)
    ax.set_ylim(0.55, 1.01)
    ax.set_ylabel(r"Independent-validation delay $R^2$")
    ax.set_title("Online budgets versus measured exhaustive support", fontsize=7.5, pad=4)
    ax.grid(axis="y", color="#d7dce2", linewidth=0.45, alpha=0.7)


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    summary = pd.read_csv(RESULT_DIR / "online_spice_budget_summary.csv")
    comparison = pd.read_csv(RESULT_DIR / "online_spice_budget_vs_exhaustive.csv")

    fig = plt.figure(figsize=(7.2, 5.4))
    grid = fig.add_gridspec(2, 6, height_ratios=[1.0, 1.08], hspace=0.43, wspace=0.72)
    axes = [
        fig.add_subplot(grid[0, 0:2]),
        fig.add_subplot(grid[0, 2:4]),
        fig.add_subplot(grid[0, 4:6]),
        fig.add_subplot(grid[1, 1:5]),
    ]
    for ax, corner, label in zip(axes[:3], ["ff", "ss", "typical"], ["a", "b", "c"]):
        draw_corner_panel(ax, summary, corner)
        add_panel_label(ax, label)
    axes[0].set_ylabel(r"Independent-validation delay $R^2$")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.995), ncol=5, fontsize=6.2, handlelength=2.0, columnspacing=1.1)

    draw_exhaustive_panel(axes[3], comparison)
    add_panel_label(axes[3], "d")
    fig.subplots_adjust(top=0.91, bottom=0.10, left=0.09, right=0.985)

    stem = OUTDIR / "fig2_online_corner_calibration"
    fig.savefig(stem.with_suffix(".png"), dpi=400, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".tiff"), dpi=600, bbox_inches="tight")
    print(f"Wrote {stem}.[png|pdf|svg|tiff]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
