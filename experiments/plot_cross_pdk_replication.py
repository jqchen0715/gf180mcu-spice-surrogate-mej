#!/usr/bin/env python3
"""Create the submission figure for locked-rule cross-PDK replication."""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
GF_ROOT = ROOT / "results/gf180_library_external_validation/online/stopping"
SKY_ROOT = ROOT / "results/sky130_cross_pdk_replication/online"
FIG_ROOT = ROOT / "manuscript/figures"
SOURCE_ROOT = ROOT / "results/sky130_cross_pdk_replication/figure_source_data"

GF_COLOR = "#356AA0"
SKY_COLOR = "#D36B35"
GRAY = "#7A7F87"
LIGHT_GRAY = "#C7CBD1"


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    gf = pd.read_csv(GF_ROOT / "stopping_decisions.csv")
    gf = gf[gf["split"].eq("confirmation")].copy()
    gf["pdk"] = "GF180MCU"
    gf["method"] = "Locked rule"

    sky = pd.read_csv(SKY_ROOT / "sky130_stopping_decisions.csv")
    method_names = {
        "gf180_locked_rule": "Locked rule",
        "fixed_64": "Fixed 64",
        "fixed_48": "Fixed 48",
    }
    sky["method"] = sky["method"].map(method_names)
    sky["pdk"] = "SKY130"

    gf_all = pd.read_csv(GF_ROOT / "stopping_confirmation_summary.csv")
    gf_all["method"] = gf_all["method"].map(
        {"locked_rule": "Locked rule", "fixed_64": "Fixed 64", "fixed_48": "Fixed 48"}
    )
    gf_all["pdk"] = "GF180MCU"
    sky_all = pd.read_csv(SKY_ROOT / "sky130_stopping_summary.csv")
    sky_all["method"] = sky_all["method"].map(method_names)
    sky_all["pdk"] = "SKY130"
    summary = pd.concat([gf_all, sky_all], ignore_index=True)
    locked = pd.concat(
        [gf, sky[sky["method"].eq("Locked rule")]], ignore_index=True
    )
    return locked, summary


def style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "font.size": 7,
            "axes.labelsize": 7,
            "axes.titlesize": 8,
            "axes.linewidth": 0.8,
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


def main() -> int:
    style()
    locked, summary = load_data()
    FIG_ROOT.mkdir(parents=True, exist_ok=True)
    SOURCE_ROOT.mkdir(parents=True, exist_ok=True)
    locked.to_csv(SOURCE_ROOT / "cross_pdk_locked_outcomes.csv", index=False)
    summary.to_csv(SOURCE_ROOT / "cross_pdk_method_summary.csv", index=False)

    fig = plt.figure(figsize=(7.15, 3.65), constrained_layout=True)
    grid = fig.add_gridspec(2, 2, width_ratios=[1.35, 1.0], height_ratios=[1, 1])
    ax_a = fig.add_subplot(grid[:, 0])
    ax_b = fig.add_subplot(grid[0, 1])
    ax_c = fig.add_subplot(grid[1, 1])

    rng = np.random.default_rng(20260718)
    for pdk, color, marker in [("GF180MCU", GF_COLOR, "o"), ("SKY130", SKY_COLOR, "D")]:
        data = locked[locked["pdk"].eq(pdk)].copy()
        jitter = rng.uniform(-0.75, 0.75, len(data))
        ax_a.scatter(
            data["stop_budget"] + jitter,
            data["delay_r2_gap_to_full"],
            s=32,
            marker=marker,
            facecolor=color,
            edgecolor="white",
            linewidth=0.55,
            alpha=0.9,
            label=f"{pdk} (n={len(data)})",
            zorder=3,
        )
    ax_a.axhline(0.02, color="#B14643", linestyle="--", linewidth=1.0)
    ax_a.text(96.3, 0.0205, "Prespecified limit", color="#8F3734", va="bottom", ha="right")
    ax_a.set_xlim(62, 98)
    ax_a.set_xticks([64, 80, 96])
    ax_a.set_ylim(-0.008, 0.025)
    ax_a.set_xlabel("SPICE calls at locked-rule stop (of 96)")
    ax_a.set_ylabel(r"Delay $R^2$ gap to measured 96-call reference")
    ax_a.set_title("Rule locked on GF180MCU remains within 0.02 on SKY130", loc="left", fontweight="bold")
    ax_a.legend(loc="upper left")
    ax_a.grid(axis="y", color="#E5E7EA", linewidth=0.6, zorder=0)

    methods = ["Locked rule", "Fixed 64", "Fixed 48"]
    x = np.arange(len(methods))
    width = 0.34
    for offset, (pdk, color) in zip(
        [-width / 2, width / 2], [("GF180MCU", GF_COLOR), ("SKY130", SKY_COLOR)]
    ):
        data = summary[summary["pdk"].eq(pdk)].set_index("method").reindex(methods)
        values = data["gap_le_0p02_rate"].to_numpy(dtype=float)
        bars = ax_b.bar(x + offset, values, width, color=color, label=pdk)
        for bar, value in zip(bars, values):
            ax_b.text(bar.get_x() + bar.get_width() / 2, value + 0.035, f"{value:.0%}", ha="center", va="bottom", fontsize=6)
    ax_b.set_ylim(0, 1.16)
    ax_b.set_xticks(x, ["Locked", "Fixed 64", "Fixed 48"])
    ax_b.set_ylabel(r"Runs with gap $\leq$ 0.02")
    ax_b.set_title("Adaptive stopping controls loss", loc="left", fontweight="bold")
    ax_b.legend(loc="upper right", ncols=2, handlelength=1.2, columnspacing=0.8)
    ax_b.grid(axis="y", color="#E5E7EA", linewidth=0.6, zorder=0)

    positions = {"GF180MCU": 0, "SKY130": 1}
    for pdk, color, marker in [("GF180MCU", GF_COLOR, "o"), ("SKY130", SKY_COLOR, "D")]:
        values = locked.loc[locked["pdk"].eq(pdk), "query_reduction_pct"].to_numpy(dtype=float)
        jitter = rng.uniform(-0.08, 0.08, len(values))
        ax_c.scatter(
            np.full(len(values), positions[pdk]) + jitter,
            values,
            s=25,
            marker=marker,
            facecolor=color,
            edgecolor="white",
            linewidth=0.5,
            alpha=0.9,
            zorder=3,
        )
        median = float(np.median(values))
        ax_c.plot([positions[pdk] - 0.18, positions[pdk] + 0.18], [median, median], color="black", linewidth=1.4)
        ax_c.text(positions[pdk], median + 2.1, f"median {median:.1f}%", ha="center", va="bottom", fontsize=6)
    ax_c.set_xlim(-0.45, 1.45)
    ax_c.set_ylim(-3, 23)
    ax_c.set_xticks([0, 1], ["GF180MCU\nconfirmation", "SKY130\nexternal replication"])
    ax_c.set_ylabel("SPICE-call reduction")
    ax_c.set_title("Savings without threshold retuning", loc="left", fontweight="bold")
    ax_c.grid(axis="y", color="#E5E7EA", linewidth=0.6, zorder=0)

    for label, axis in zip(["a", "b", "c"], [ax_a, ax_b, ax_c]):
        axis.text(-0.13, 1.06, label, transform=axis.transAxes, fontsize=9, fontweight="bold", va="top")

    base = FIG_ROOT / "fig4_cross_pdk_replication"
    fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(base.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(base.with_suffix(".tiff"), dpi=600, bbox_inches="tight")
    fig.savefig(base.with_suffix(".png"), dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(base)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
