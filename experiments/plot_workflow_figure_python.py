#!/usr/bin/env python3
"""Draw the publication workflow figure for the cross-PDK study."""

from __future__ import annotations

import os
from pathlib import Path

Path("/private/tmp/matplotlib-cache").mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/matplotlib-cache")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle


matplotlib.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "font.size": 7.0,
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
        "axes.linewidth": 0.7,
    }
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "manuscript" / "figures" / "fig1_workflow"

INK = "#17212b"
MUTED = "#52606d"
RULE = "#aeb8c2"
BLUE = "#3d6f94"
BLUE_LIGHT = "#e8f0f5"
TEAL = "#2f7f74"
TEAL_LIGHT = "#e7f2ef"
ORANGE = "#c06b35"
ORANGE_LIGHT = "#f8eee7"
GRAY_LIGHT = "#f4f6f7"


def box(ax, x, y, w, h, title, detail="", fill="white", edge=RULE, lw=0.75,
        title_color=INK, align="left"):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=fill, edgecolor=edge, linewidth=lw))
    tx = x + 0.018 if align == "left" else x + w / 2
    ha = "left" if align == "left" else "center"
    ax.text(tx, y + h * 0.64, title, ha=ha, va="center", color=title_color,
            fontsize=7.0, weight="bold")
    if detail:
        ax.text(tx, y + h * 0.27, detail, ha=ha, va="center", color=MUTED,
                fontsize=5.75, linespacing=1.15)


def arrow(ax, p1, p2, color=MUTED, lw=0.9, style="-|>", rad=0.0, dashed=False):
    ax.add_patch(
        FancyArrowPatch(
            p1,
            p2,
            arrowstyle=style,
            mutation_scale=8.5,
            linewidth=lw,
            color=color,
            linestyle="--" if dashed else "-",
            connectionstyle=f"arc3,rad={rad}",
            shrinkA=0,
            shrinkB=0,
        )
    )


def panel_label(ax, x, y, letter, title):
    ax.text(x, y, letter, fontsize=9.0, weight="bold", color=INK, ha="left", va="top")
    ax.text(x + 0.032, y, title, fontsize=8.0, weight="bold", color=INK, ha="left", va="top")


def draw() -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.15))
    fig.subplots_adjust(left=0.025, right=0.985, bottom=0.04, top=0.98)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    panel_label(ax, 0.02, 0.965, "a", "Validation-blind simulator-in-the-loop acquisition")
    ax.plot([0.02, 0.615], [0.915, 0.915], color=INK, lw=0.75)

    ax.text(0.035, 0.865, "VISIBLE TO ACQUISITION", fontsize=5.7, weight="bold", color=TEAL)
    box(ax, 0.035, 0.700, 0.165, 0.125, "Base SPICE set", "two process corners\nmeasured labels", TEAL_LIGHT, TEAL)
    box(ax, 0.235, 0.700, 0.165, 0.125, "Support model", "PDK-specific fit\ndelay and power", BLUE_LIGHT, BLUE)
    box(ax, 0.435, 0.700, 0.165, 0.125, "Held-out corner", "96 feature-only points\nlabels initially hidden", GRAY_LIGHT, RULE)
    arrow(ax, (0.200, 0.762), (0.235, 0.762), TEAL)
    arrow(ax, (0.400, 0.762), (0.435, 0.762), BLUE)

    box(ax, 0.435, 0.500, 0.165, 0.115, "Select batch", "cell-balanced\nfeature coverage", "white", BLUE)
    box(ax, 0.235, 0.500, 0.165, 0.115, "Fresh ngspice", "write netlist\nmeasure selected labels", ORANGE_LIGHT, ORANGE)
    box(ax, 0.035, 0.500, 0.165, 0.115, "Update support", "append measurements\nrefit model", TEAL_LIGHT, TEAL)
    arrow(ax, (0.518, 0.700), (0.518, 0.615), BLUE)
    arrow(ax, (0.435, 0.557), (0.400, 0.557), ORANGE)
    arrow(ax, (0.235, 0.557), (0.200, 0.557), TEAL)
    arrow(ax, (0.118, 0.615), (0.295, 0.700), TEAL, rad=0.25)
    ax.text(0.175, 0.655, "repeat", fontsize=5.5, color=TEAL, ha="center")

    ax.plot([0.035, 0.600], [0.440, 0.440], color=RULE, lw=0.65, linestyle=(0, (3, 2)))
    ax.text(0.035, 0.410, "EVALUATION ONLY", fontsize=5.7, weight="bold", color=ORANGE)
    box(ax, 0.035, 0.260, 0.180, 0.115, "Independent validation", "labels never guide\nselection or stopping", "white", ORANGE)
    box(ax, 0.245, 0.260, 0.155, 0.115, "Budget trajectory", "R2, worst family,\nrank and time", "white", RULE)
    box(ax, 0.430, 0.260, 0.170, 0.115, "Measured reference", "complete all 96 calls\nquantify gap and savings", GRAY_LIGHT, INK)
    arrow(ax, (0.215, 0.318), (0.245, 0.318), ORANGE)
    arrow(ax, (0.400, 0.318), (0.430, 0.318), MUTED)
    arrow(ax, (0.318, 0.500), (0.318, 0.375), MUTED, dashed=True)
    ax.text(0.326, 0.425, "predictions only", fontsize=5.3, color=MUTED, ha="left", va="center")

    ax.plot([0.635, 0.635], [0.08, 0.965], color=RULE, lw=0.7)
    panel_label(ax, 0.665, 0.965, "b", "Locked-rule cross-PDK validation")
    ax.plot([0.665, 0.98], [0.915, 0.915], color=INK, lw=0.75)

    box(ax, 0.690, 0.735, 0.265, 0.120, "GF180MCU development", "9 pools select observable thresholds", BLUE_LIGHT, BLUE, align="center")
    arrow(ax, (0.822, 0.735), (0.822, 0.675), BLUE)
    box(ax, 0.690, 0.555, 0.265, 0.120, "LOCK STOPPING RULE", "minimum budget + prequential error\nprediction stability + feature coverage", "white", INK, 1.15, align="center")

    arrow(ax, (0.822, 0.555), (0.735, 0.470), MUTED)
    arrow(ax, (0.822, 0.555), (0.910, 0.470), MUTED)
    box(ax, 0.655, 0.330, 0.160, 0.140, "GF180MCU", "6 untouched pools\nmedian 88/96 calls\n5/6 gap <= 0.02", BLUE_LIGHT, BLUE, align="center")
    box(ax, 0.840, 0.330, 0.160, 0.140, "SKY130", "15 external pools\nmedian 80/96 calls\n15/15 gap <= 0.02", TEAL_LIGHT, TEAL, align="center")

    ax.text(0.822, 0.275, "NO THRESHOLD RETUNING", ha="center", va="center",
            fontsize=6.0, weight="bold", color=ORANGE)
    ax.plot([0.690, 0.955], [0.250, 0.250], color=ORANGE, lw=0.8)
    ax.text(0.822, 0.195, "PDK-specific model retraining", ha="center", fontsize=6.0, color=INK)
    ax.text(0.822, 0.155, "pre-layout; one sensitized arc per family", ha="center", fontsize=5.7, color=MUTED)
    ax.text(0.822, 0.115, "not zero-shot transfer or complete Liberty characterization", ha="center", fontsize=5.5, color=MUTED)

    for suffix, kwargs in (
        (".pdf", {}),
        (".svg", {}),
        (".png", {"dpi": 400}),
        (".tiff", {"dpi": 600}),
    ):
        fig.savefig(OUT.with_suffix(suffix), bbox_inches="tight", facecolor="white", **kwargs)
    plt.close(fig)


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    draw()
    print(f"Wrote {OUT}.pdf/.svg/.png/.tiff")
