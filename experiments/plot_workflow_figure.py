#!/usr/bin/env python3
"""Draw the deterministic simulator-in-the-loop workflow figure."""

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
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

matplotlib.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "font.size": 7,
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
    }
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTDIR = PROJECT_ROOT / "manuscript" / "figures"


def add_box(ax, x, y, w, h, title, body, facecolor, edgecolor="#334155"):
    box = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.012,rounding_size=0.012",
        linewidth=1.0,
        edgecolor=edgecolor,
        facecolor=facecolor,
    )
    ax.add_patch(box)
    ax.text(x + w / 2, y + h * 0.72, title, ha="center", va="center", fontsize=6.8, weight="bold", color="#172033")
    ax.text(x + w / 2, y + h * 0.34, body, ha="center", va="center", fontsize=5.45, color="#374151", linespacing=1.16)


def add_arrow(ax, start, end, color="#475569", rad=0.0):
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=11,
        linewidth=1.15,
        color=color,
        connectionstyle=f"arc3,rad={rad}",
    )
    ax.add_patch(arrow)


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.2, 4.25))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.5,
        0.965,
        "Deterministic simulator-in-the-loop corner calibration",
        ha="center",
        va="top",
        fontsize=11,
        weight="bold",
        color="#111827",
    )
    ax.text(
        0.5,
        0.915,
        "Validation labels remain hidden from acquisition; every selected support point launches ngspice",
        ha="center",
        va="top",
        fontsize=7.2,
        color="#4b5563",
    )

    boxes = {
        "configuration": (0.035, 0.66, 0.205, 0.17, "Configuration audit", "GF180MCU / ngspice 46\nstatistical switches forced off\nmodel, netlist and log retained", "#dce9f8"),
        "datasets": (0.278, 0.66, 0.205, 0.17, "Independent SPICE sets", "Primary: 320 rows\nValidation: 480 rows\nINV, NAND2, NOR2 and XOR2", "#dff1ea"),
        "holdout": (0.522, 0.66, 0.205, 0.17, "Unseen-corner setup", "Train on two process corners\n96 feature-only candidates\nin the held-out corner", "#f6ebcc"),
        "select": (0.278, 0.36, 0.205, 0.17, "Validation-blind selection", "Four-query batches\none point per cell\nmaximize feature-space coverage", "#e9e3f5"),
        "query": (0.522, 0.36, 0.205, 0.17, "SPICE query and update", "Launch ngspice for selected rows\nappend measured delay and power\nretrain the support model", "#f6dfeb"),
        "evaluate": (0.765, 0.36, 0.205, 0.17, "Independent evaluation", "Validation set used only here\n5 seeds x 3 corners\ncompare budgets and strategies", "#f3e7d6"),
        "reference": (0.522, 0.08, 0.205, 0.17, "96-point measured reference", "Complete all 96 candidates\nquantify query and time savings\naudit repeated simulations", "#d8f1ee"),
        "boundary": (0.765, 0.08, 0.205, 0.17, "Claim boundary", "Early transistor-level exploration\nnot layout-extracted sign-off\nnot full Liberty characterization", "#eef0f3"),
    }

    for values in boxes.values():
        add_box(ax, *values)

    add_arrow(ax, (0.240, 0.745), (0.278, 0.745))
    add_arrow(ax, (0.483, 0.745), (0.522, 0.745))
    add_arrow(ax, (0.625, 0.66), (0.405, 0.53), rad=0.12)
    add_arrow(ax, (0.483, 0.445), (0.522, 0.445))
    add_arrow(ax, (0.727, 0.445), (0.765, 0.445))
    add_arrow(ax, (0.625, 0.36), (0.625, 0.25))
    add_arrow(ax, (0.727, 0.165), (0.765, 0.165))

    ax.text(
        0.5,
        0.035,
        "Online support labels come from fresh ngspice runs; validation labels never guide selection or stopping.",
        ha="center",
        va="bottom",
        fontsize=6.8,
        color="#4b5563",
    )

    png = OUTDIR / "fig1_workflow.png"
    pdf = OUTDIR / "fig1_workflow.pdf"
    svg = OUTDIR / "fig1_workflow.svg"
    tiff = OUTDIR / "fig1_workflow.tiff"
    fig.savefig(png, dpi=400, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(svg, bbox_inches="tight")
    fig.savefig(tiff, dpi=600, bbox_inches="tight")
    print(f"Wrote {png}")
    print(f"Wrote {pdf}")
    return 0


if __name__ == "__main__":
    # Keep this historical entry point while delegating to the publication version.
    from plot_workflow_figure_python import OUT, draw

    OUT.parent.mkdir(parents=True, exist_ok=True)
    draw()
    print(f"Wrote {OUT}.pdf/.svg/.png/.tiff")
