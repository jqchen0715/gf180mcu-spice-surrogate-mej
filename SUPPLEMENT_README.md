# MEJ Reproducibility Supplement

This archive supports the manuscript:

A Source-Aware SPICE-Grounded Workflow for Sample-Efficient GF180MCU Standard-Cell Exploration

## Contents

- `data/dataset_v2_spice_320.csv`: primary publication-facing GF180MCU/ngspice dataset.
- `data/dataset_v3_spice_480.csv`: independent GF180MCU/ngspice validation dataset for scale-up and corner-support checks.
- `previous_work/legacy_data_and_scripts/dataset_hybrid_combined.csv`: legacy low-fidelity inverter dataset used only for the source-aware ablation.
- `spice_v2/`: SPICE data-generation script and schema/status notes.
- `experiments/`: experiment and plotting scripts for the manuscript results.
- `results/`: publication-facing result tables, reports, and plots.
- `manuscript/figures/`: manuscript figure files in PDF and PNG formats.
- `README.md` and `REPRODUCIBILITY.md`: repository overview and reproduction notes.

## Exclusions

This archive intentionally excludes the local virtual environment, the GF180MCU PDK checkout, debug datasets, generated ngspice logs/netlists, and legacy exploratory evidence files. Users should obtain GF180MCU PDK files from the official source if they want to regenerate SPICE data.

## Scope

The workflow supports early standard-cell design-space exploration. It is not a SPICE replacement, sign-off flow, full Liberty characterization, or production standard-cell library generator.
