#!/usr/bin/env python3
"""Plot the released-CDL, stopping, and Liberty external-validation evidence."""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROOT = PROJECT_ROOT / "results" / "gf180_library_external_validation"
FIGURE_ROOT = PROJECT_ROOT / "manuscript" / "figures"
TRAJECTORY = ROOT / "online" / "library_online_trajectory.csv"
STOPPING = ROOT / "online" / "stopping" / "stopping_decisions.csv"
LIBERTY = ROOT / "liberty_crosscheck" / "liberty_spice_point_comparison.csv"
METRICS = ROOT / "liberty_crosscheck" / "liberty_spice_agreement_metrics.csv"


COLORS = {"ff": "#C65D4B", "ss": "#47789D", "typical": "#4F8A70"}
LABELS = {"ff": "ff", "ss": "ss", "typical": "typical"}


def style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "font.size": 7,
            "axes.labelsize": 7,
            "axes.titlesize": 8,
            "axes.linewidth": 0.7,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.labelsize": 6.5,
            "ytick.labelsize": 6.5,
            "legend.fontsize": 6.5,
            "legend.frameon": False,
            "pdf.fonttype": 42,
            "svg.fonttype": "none",
        }
    )


def panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(-0.18, 1.06, label, transform=ax.transAxes, fontsize=9, fontweight="bold", va="top")


def main() -> int:
    style()
    trajectory = pd.read_csv(TRAJECTORY)
    stopping = pd.read_csv(STOPPING)
    liberty = pd.read_csv(LIBERTY)
    metrics = pd.read_csv(METRICS)
    confirmation = stopping[stopping["split"].eq("confirmation")].copy()
    overall = metrics[(metrics["group"] == "all") & (metrics["value"] == "all")].iloc[0]

    fig = plt.figure(figsize=(7.2, 3.05), constrained_layout=True)
    grid = fig.add_gridspec(1, 3, width_ratios=[1.35, 0.92, 1.05])
    ax_a = fig.add_subplot(grid[0, 0])
    ax_b = fig.add_subplot(grid[0, 1])
    ax_c = fig.add_subplot(grid[0, 2])

    for corner in ("ff", "ss", "typical"):
        subset = trajectory[trajectory["heldout_corner"].eq(corner)]
        grouped = subset.groupby("support_budget")["delay_r2"]
        x = np.asarray(sorted(subset["support_budget"].unique()), dtype=float)
        median = grouped.median().reindex(x).to_numpy(dtype=float)
        q25 = grouped.quantile(0.25).reindex(x).to_numpy(dtype=float)
        q75 = grouped.quantile(0.75).reindex(x).to_numpy(dtype=float)
        ax_a.plot(x, median, marker="o", ms=3.2, lw=1.4, color=COLORS[corner], label=LABELS[corner])
        ax_a.fill_between(x, q25, q75, color=COLORS[corner], alpha=0.15, linewidth=0)
    ax_a.axvline(48, color="#777777", lw=0.8, ls="--")
    ax_a.set_xlabel("Measured support queries (of 96)")
    ax_a.set_ylabel(r"Independent-validation delay $R^2$")
    ax_a.set_title("Released-CDL corner calibration", loc="left", pad=6)
    ax_a.set_xticks([0, 16, 32, 48, 64, 80, 96])
    ax_a.grid(axis="y", color="#DDDDDD", lw=0.5)
    ax_a.legend(ncol=3, loc="lower right", handlelength=1.5, columnspacing=0.8)
    panel_label(ax_a, "a")

    corner_offsets = {"ff": -1.4, "ss": 0.0, "typical": 1.4}
    for corner in ("ff", "ss", "typical"):
        subset = confirmation[confirmation["heldout_corner"].eq(corner)]
        seed_offsets = subset["seed"].map({3: -0.35, 4: 0.35}).fillna(0.0)
        ax_b.scatter(
            subset["stop_budget"] + corner_offsets[corner] + seed_offsets,
            subset["delay_r2_gap_to_full"],
            s=28,
            color=COLORS[corner],
            edgecolor="white",
            linewidth=0.6,
            alpha=0.95,
            label=LABELS[corner],
        )
    ax_b.axhline(0.02, color="#B24A3A", lw=0.9, ls="--", label=r"gap $=0.02$")
    ax_b.axhline(0, color="#777777", lw=0.6)
    ax_b.set_xlim(25, 100)
    ax_b.set_xticks([32, 48, 64, 80, 96])
    ax_b.set_xlabel("Validation-blind stop budget")
    ax_b.set_ylabel(r"Delay-$R^2$ gap to 96-query reference")
    ax_b.set_title("Locked-rule confirmation", loc="left", pad=6)
    ax_b.grid(axis="y", color="#DDDDDD", lw=0.5)
    ax_b.text(
        0.04,
        0.96,
        f"n={len(confirmation)} independent pools\nmedian stop={confirmation['stop_budget'].median():.0f}",
        transform=ax_b.transAxes,
        ha="left",
        va="top",
        fontsize=6.5,
    )
    panel_label(ax_b, "b")

    for corner in ("ff", "ss", "typical"):
        subset = liberty[liberty["corner"].eq(corner)]
        ax_c.scatter(
            subset["liberty_delay_avg_ns"],
            subset["delay_avg_ns"],
            s=8,
            color=COLORS[corner],
            alpha=0.48,
            linewidth=0,
            label=LABELS[corner],
        )
    limits = [
        min(liberty["liberty_delay_avg_ns"].min(), liberty["delay_avg_ns"].min()) * 0.82,
        max(liberty["liberty_delay_avg_ns"].max(), liberty["delay_avg_ns"].max()) * 1.15,
    ]
    ax_c.plot(limits, limits, color="#555555", lw=0.9, ls="--")
    ax_c.set_xscale("log")
    ax_c.set_yscale("log")
    ax_c.set_xlim(limits)
    ax_c.set_ylim(limits)
    ax_c.set_xlabel("Released Liberty delay (ns)")
    ax_c.set_ylabel("Fresh ngspice/CDL delay (ns)")
    ax_c.set_title("Partial Liberty compatibility", loc="left", pad=6)
    ax_c.grid(which="major", color="#DDDDDD", lw=0.5)
    ax_c.text(
        0.04,
        0.96,
        rf"$n$={len(liberty)} points" + "\n" + rf"Spearman $\rho$={overall['spearman_rho']:.3f}" + "\n" + f"median APE={overall['median_absolute_percentage_error']:.1f}%",
        transform=ax_c.transAxes,
        ha="left",
        va="top",
        fontsize=6.5,
    )
    panel_label(ax_c, "c")

    FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
    stem = FIGURE_ROOT / "fig3_official_library_validation"
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".png"), dpi=300, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".tiff"), dpi=600, bbox_inches="tight")
    plt.close(fig)
    print(stem)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
