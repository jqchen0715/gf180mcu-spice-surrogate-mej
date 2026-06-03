#!/usr/bin/env python3
"""Draw the workflow figure for the Microelectronics Journal manuscript."""

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


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTDIR = PROJECT_ROOT / "manuscript" / "figures"


def add_box(ax, x, y, w, h, title, body, facecolor, edgecolor="#2f3b52"):
    box = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.018,rounding_size=0.025",
        linewidth=1.3,
        edgecolor=edgecolor,
        facecolor=facecolor,
    )
    ax.add_patch(box)
    ax.text(x + w / 2, y + h * 0.72, title, ha="center", va="center", fontsize=10, weight="bold", color="#1f2937")
    ax.text(x + w / 2, y + h * 0.34, body, ha="center", va="center", fontsize=7.9, color="#374151", linespacing=1.22)


def add_arrow(ax, start, end, color="#475569", rad=0.0):
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=14,
        linewidth=1.5,
        color=color,
        connectionstyle=f"arc3,rad={rad}",
    )
    ax.add_patch(arrow)


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12.8, 7.0))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.5,
        0.965,
        "Source-aware SPICE-efficient surrogate workflow",
        ha="center",
        va="top",
        fontsize=15,
        weight="bold",
        color="#111827",
    )
    ax.text(
        0.5,
        0.915,
        "Early design-space exploration with explicit provenance and SPICE re-validation",
        ha="center",
        va="top",
        fontsize=10,
        color="#4b5563",
    )

    boxes = {
        "spice": (0.055, 0.66, 0.20, 0.17, "SPICE simulation", "GF180MCU/ngspice\ncontrolled INV, NAND2,\nNOR2, XOR2 arcs", "#dbeafe"),
        "dataset": (0.315, 0.66, 0.20, 0.17, "SPICE datasets", "320 primary + 480 validation\nstatus=ok, SPICE_GF180MCU\nnetlist + log + model path", "#e0f2fe"),
        "audit": (0.575, 0.66, 0.20, 0.17, "Provenance audit", "Legacy 155-row source\nused only as a\nnegative-control auxiliary", "#fef3c7"),
        "features": (0.055, 0.39, 0.20, 0.17, "Feature encoding", "Sizing, Vdd, Temp,\nCload, slew, corner,\ncell type, input arc", "#dcfce7"),
        "models": (0.315, 0.39, 0.20, 0.17, "Surrogate models", "Ridge, random forest,\ngradient boosting,\nMLP", "#ede9fe"),
        "transfer": (0.575, 0.39, 0.20, 0.17, "Evaluation", "Random split, cell transfer\nvalidation dataset test\ncorner-support calibration", "#fce7f3"),
        "active": (0.315, 0.12, 0.20, 0.17, "Active learning", "Random, uncertainty,\nhybrid acquisition over\nSPICE-measured pool", "#ccfbf1"),
        "candidate": (0.575, 0.12, 0.20, 0.17, "Candidate check", "Surrogate ranks points;\nheld-out primary and\nvalidation rows verify candidates", "#ffedd5"),
        "boundary": (0.815, 0.36, 0.15, 0.23, "Boundary", "Early exploration only\nnot sign-off\nnot full Liberty", "#f3f4f6"),
    }

    for values in boxes.values():
        add_box(ax, *values)

    add_arrow(ax, (0.255, 0.74), (0.315, 0.74))
    add_arrow(ax, (0.515, 0.74), (0.575, 0.74))
    add_arrow(ax, (0.155, 0.66), (0.155, 0.55))
    add_arrow(ax, (0.255, 0.47), (0.315, 0.47))
    add_arrow(ax, (0.515, 0.47), (0.575, 0.47))
    add_arrow(ax, (0.415, 0.39), (0.415, 0.28))
    add_arrow(ax, (0.515, 0.20), (0.575, 0.20))
    add_arrow(ax, (0.775, 0.47), (0.815, 0.47))
    add_arrow(ax, (0.775, 0.20), (0.89, 0.36), rad=0.18)

    ax.text(
        0.5,
        0.035,
        "Final design points remain subject to conventional SPICE re-simulation under the intended PDK, PVT, load, slew, and layout conditions.",
        ha="center",
        va="bottom",
        fontsize=9,
        color="#4b5563",
    )

    png = OUTDIR / "fig1_workflow.png"
    pdf = OUTDIR / "fig1_workflow.pdf"
    fig.savefig(png, dpi=300, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    print(f"Wrote {png}")
    print(f"Wrote {pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
