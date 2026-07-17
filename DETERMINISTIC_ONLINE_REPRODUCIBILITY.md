# Deterministic Simulator-in-the-Loop Reproducibility

Updated: 2026-07-15

This document describes the controlled GF180MCU stage of the manuscript
**Cross-PDK Validation of a Deterministic Simulator-in-the-Loop Protocol for
Standard-Cell Corner Calibration**.

## 1. Environment

- ngspice 46
- GF180MCU PDK commit `de3240d7529a6970437ac3344820aaae7839f215`
- primitive model file `sm141064.ngspice`
- device models `nmos_3p3` and `pmos_3p3`
- Python dependencies from `requirements.txt`

The PDK is not redistributed. Obtain it from the official repositories cited in
the manuscript.

## 2. Deterministic Configuration

The generator defaults to `--statistical-mode off` and writes the following
override after the GF180MCU design include:

```spice
.param sw_stat_global=0 sw_stat_mismatch=0
```

This setting defines deterministic corner characterization. It is not a
replacement for a separately designed global-variation or mismatch study.

## 3. Publication Datasets

```text
data/dataset_primary_deterministic_320.csv
data/dataset_validation_deterministic_480.csv
```

Regenerate them with separate netlist and log directories:

```bash
python spice_v2/generate_spice_dataset.py \
  --vdd-min 1.62 --vdd-max 1.98 \
  --cells INV NAND2 NOR2 XOR2 \
  --samples-per-cell 80 --seed 20260530 \
  --sample-id-offset 8000000 \
  --statistical-mode off \
  --netlist-dir spice_v2/netlists_deterministic_primary_320 \
  --log-dir spice_v2/logs_deterministic_primary_320 \
  --output data/dataset_primary_deterministic_320.csv

python spice_v2/generate_spice_dataset.py \
  --vdd-min 1.62 --vdd-max 1.98 \
  --cells INV NAND2 NOR2 XOR2 \
  --samples-per-cell 120 --seed 20260602 \
  --sample-id-offset 9000000 \
  --statistical-mode off \
  --netlist-dir spice_v2/netlists_deterministic_validation_480 \
  --log-dir spice_v2/logs_deterministic_validation_480 \
  --output data/dataset_validation_deterministic_480.csv
```

## 4. Acquisition Policy Development

The diversity/uncertainty weight is selected using primary data only:

```bash
python experiments/tune_corner_acquisition_weight.py \
  --dataset data/dataset_primary_deterministic_320.csv \
  --outdir results/deterministic_corner_acquisition_weight_tuning
```

The locked setting is uncertainty weight 0 and diversity weight 1.

## 5. Genuine Online SPICE Experiment

```bash
python experiments/online_spice_corner_calibration.py \
  --primary-dataset data/dataset_primary_deterministic_320.csv \
  --validation-dataset data/dataset_validation_deterministic_480.csv \
  --outdir results/online_spice_deterministic \
  --seeds 0 1 2 3 4 \
  --heldout-corners ff ss typical \
  --candidate-per-cell 24 \
  --max-support 48 --batch-size 4 --workers 4 \
  --n-estimators 240 \
  --uncertainty-weight 0 --diversity-weight 1 \
  --resume
```

Every selected point launches ngspice. Validation labels are used only to score
each completed budget and are unavailable to acquisition and stopping.

## 6. Measured Exhaustive Reference

```bash
python experiments/complete_online_exhaustive_reference.py \
  --primary-dataset data/dataset_primary_deterministic_320.csv \
  --validation-dataset data/dataset_validation_deterministic_480.csv \
  --online-outdir results/online_spice_deterministic \
  --workers 4 --n-estimators 240 --resume
```

This step completes every 96-point seed-corner pool and audits repeated
candidate simulations before retaining one row per candidate.

## 7. Diagnostics, Figures, and Manuscript Audit

```bash
python experiments/replay_online_prequential_diagnostics.py \
  --primary-dataset data/dataset_primary_deterministic_320.csv \
  --online-outdir results/online_spice_deterministic \
  --n-estimators 240

python experiments/plot_workflow_figure.py
python experiments/plot_deterministic_online_results.py
python tools/audit_deterministic_online_manuscript.py
```

## 8. New Zenodo Version Checklist

The next versioned archive should contain:

- deterministic primary and validation CSV files;
- their generated netlists and ngspice logs;
- all scripts listed above;
- `results/online_spice_deterministic/`, including `runs/` and
  `exhaustive_reference/`;
- structured deterministic robustness and external-validation outputs;
- manuscript source, compiled PDF, figure source files, and numeric audit;
- exact package versions, checksums, and the PDK commit identifier.

The GitHub copy may omit the thousands of per-query netlist/log files to keep
the repository manageable. The versioned Zenodo archive should include them.
