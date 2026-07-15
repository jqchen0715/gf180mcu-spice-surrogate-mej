# Reproducibility Notes for the Revised SCI Submission

> **Superseded for the current manuscript.** This file documents the preceding
> static-table study and is retained for release history. Use
> `DETERMINISTIC_ONLINE_REPRODUCIBILITY.md` for the current deterministic
> simulator-in-the-loop study.

Updated: 2026-07-09

This document describes how to reproduce the publication-facing dataset, experiments, and figures for the manuscript:

**SPICE-Efficient Candidate Screening and Corner-Support Calibration for GF180MCU Standard-Cell Exploration**

The project is intended for early design-space exploration. It is not a sign-off flow, a production standard-cell library generator, or a full Liberty characterization package.

## 1. Publication Datasets

Primary dataset:

```text
data/dataset_v2_spice_320.csv
```

The dataset contains 320 publication-eligible GF180MCU/ngspice rows:

| Cell | Rows |
|---|---:|
| INV | 80 |
| NAND2 | 80 |
| NOR2 | 80 |
| XOR2 | 80 |

Independent validation dataset:

```text
data/dataset_v3_spice_480.csv
```

The V3 dataset contains 480 publication-eligible GF180MCU/ngspice rows:

| Cell | Rows |
|---|---:|
| INV | 120 |
| NAND2 | 120 |
| NOR2 | 120 |
| XOR2 | 120 |

The V3 dataset has a balanced corner distribution: 160 ff rows, 160 ss rows, and 160 typical rows, with 40 rows per cell-corner pair.

Publication-eligible rows must satisfy:

- `status == ok`
- `fidelity == SPICE_GF180MCU`
- non-empty GF180MCU `model_file`
- retained generated `netlist_path`
- retained ngspice `log_path`
- `simulator == ngspice`

Generic debug datasets and dry-run datasets are not used in the manuscript conclusions.

## 2. SPICE Data Generation

The data-generation script is:

```text
spice_v2/generate_spice_dataset.py
```

Relevant documentation:

```text
spice_v2/README.md
spice_v2/schema.md
spice_v2/status.md
```

The local verified environment used:

- ngspice 46
- GF180MCU primitive devices `nmos_3p3` and `pmos_3p3`
- GF180MCU model file `sm141064.ngspice`
- channel length 0.28 um
- supply range 1.62-1.98 V

Check whether the local PDK/model setup is usable:

```bash
.venv/bin/python spice_v2/generate_spice_dataset.py --check-only
```

Regenerate the publication-scale dataset:

```bash
.venv/bin/python spice_v2/generate_spice_dataset.py \
  --vdd-min 1.62 \
  --vdd-max 1.98 \
  --cells INV NAND2 NOR2 XOR2 \
  --samples-per-cell 80 \
  --output data/dataset_v2_spice_320.csv
```

Regenerate the independent V3 validation dataset without overwriting V2 netlists/logs:

```bash
.venv/bin/python spice_v2/generate_spice_dataset.py \
  --vdd-min 1.62 \
  --vdd-max 1.98 \
  --cells INV NAND2 NOR2 XOR2 \
  --samples-per-cell 120 \
  --seed 20260602 \
  --sample-id-offset 20000 \
  --netlist-dir spice_v2/netlists_v3_480 \
  --log-dir spice_v2/logs_v3_480 \
  --output data/dataset_v3_spice_480.csv
```

If the GF180MCU model file is installed elsewhere, pass the exact model path using the script option documented in `spice_v2/README.md`.

## 3. Main Experiments

Run commands from the project root.

### 3.0 SCI-Revision Enhanced Evaluation

```bash
.venv/bin/python experiments/sci_revision_enhanced_evaluation.py
.venv/bin/python experiments/plot_sci_revision_checks.py
```

Expected outputs:

```text
results/sci_revision/sci_model_zoo_repeated.csv
results/sci_revision/sci_model_zoo_summary.csv
results/sci_revision/sci_external_validation_all_models.csv
results/sci_revision/sci_external_validation_all_models_summary.csv
results/sci_revision/sci_friedman_tests.csv
results/sci_revision/sci_wilcoxon_tests.csv
results/sci_revision/sci_ranking_metrics.csv
results/sci_revision/sci_ranking_metrics_summary.csv
results/sci_revision/sci_conformal_intervals.csv
results/sci_revision/sci_conformal_intervals_summary.csv
results/sci_revision/sci_permutation_feature_importance.csv
results/sci_revision/sci_spice_runtime_parsed.csv
results/sci_revision/sci_spice_runtime_summary.csv
results/sci_revision/sci_revision_enhanced_evaluation_report.md
manuscript/figures/fig8_sci_revision_checks.png
manuscript/figures/fig8_sci_revision_checks.pdf
```

This experiment adds GPR, XGBoost, LightGBM, and CatBoost baselines, primary-to-validation testing for all model families, Friedman and paired Wilcoxon tests, ranking metrics, split conformal intervals, permutation feature importance, and parsed ngspice runtime summaries.

### 3.1 Baselines and Cross-Cell Transfer

```bash
.venv/bin/python experiments/v2_baseline_transfer.py
```

Expected outputs:

```text
results/v2/v2_baseline_transfer_results.csv
results/v2/v2_baseline_transfer_report.md
results/v2/v2_dataset_summary.json
```

Transfer-curve figure:

```bash
.venv/bin/python experiments/plot_v2_transfer.py
```

Expected outputs:

```text
results/v2/v2_fewshot_transfer_curves.png
results/v2/v2_fewshot_transfer_curves.pdf
```

### 3.2 Source-Fusion and Weighting Ablation

```bash
.venv/bin/python experiments/source_aware_ablation.py
```

Expected outputs:

```text
results/source_aware/source_aware_ablation_results.csv
results/source_aware/source_aware_ablation_summary.csv
results/source_aware/source_aware_ablation_summary.json
results/source_aware/source_aware_ablation_report.md
```

This experiment treats the legacy 155-row inverter dataset as low-fidelity auxiliary data, not as SPICE-equivalent evidence.

### 3.3 Robustness, Feature Ablation, and Candidate-Ranking Baseline

```bash
.venv/bin/python experiments/v2_robustness_ablation.py
```

Expected outputs:

```text
results/v2_robustness/v2_model_zoo_repeated.csv
results/v2_robustness/v2_model_zoo_repeated_summary.csv
results/v2_robustness/v2_feature_ablation.csv
results/v2_robustness/v2_feature_ablation_summary.csv
results/v2_robustness/v2_learning_curve.csv
results/v2_robustness/v2_learning_curve_summary.csv
results/v2_robustness/v2_corner_holdout.csv
results/v2_robustness/v2_corner_holdout_summary.csv
results/v2_robustness/v2_transfer_robustness.csv
results/v2_robustness/v2_transfer_robustness_summary.csv
results/v2_robustness/v2_candidate_ranking_robustness.csv
results/v2_robustness/v2_candidate_ranking_summary.csv
results/v2_robustness/v2_robustness_summary.json
results/v2_robustness/v2_robustness_report.md
```

This experiment uses only the new 320-row V2 SPICE dataset. It runs repeated random-split model benchmarking, feature-group ablation, learning curves, leave-one-corner-out stress testing, repeated leave-one-cell-out transfer, and candidate-ranking enrichment against random selection.

V3 scale-up robustness can be reproduced with:

```bash
.venv/bin/python experiments/v2_robustness_ablation.py \
  --dataset data/dataset_v3_spice_480.csv \
  --outdir results/v3_robustness \
  --output-prefix v3 \
  --learning-curve-rows 40 80 120 160 240 320 384
```

Expected outputs:

```text
results/v3_robustness/v3_model_zoo_repeated.csv
results/v3_robustness/v3_model_zoo_repeated_summary.csv
results/v3_robustness/v3_feature_ablation.csv
results/v3_robustness/v3_feature_ablation_summary.csv
results/v3_robustness/v3_learning_curve.csv
results/v3_robustness/v3_learning_curve_summary.csv
results/v3_robustness/v3_corner_holdout.csv
results/v3_robustness/v3_corner_holdout_summary.csv
results/v3_robustness/v3_transfer_robustness.csv
results/v3_robustness/v3_transfer_robustness_summary.csv
results/v3_robustness/v3_candidate_ranking_robustness.csv
results/v3_robustness/v3_candidate_ranking_summary.csv
results/v3_robustness/v3_robustness_summary.json
results/v3_robustness/v3_robustness_report.md
```

### 3.4 External V3 Validation and Corner-Support Calibration

```bash
.venv/bin/python experiments/v3_scale_and_corner_support.py
```

Expected outputs:

```text
results/v3_scale_validation/v3_external_validation.csv
results/v3_scale_validation/v3_external_candidate_ranking.csv
results/v3_scale_validation/v3_external_candidate_ranking_summary.csv
results/v3_scale_validation/v3_corner_support.csv
results/v3_scale_validation/v3_corner_support_summary.csv
results/v3_scale_validation/v3_scale_validation_summary.json
results/v3_scale_validation/v3_scale_validation_report.md
```

This experiment trains on the V2 primary dataset, evaluates directly on the independently generated V3 dataset, and then tests how many same-corner support rows are needed to mitigate weak zero-shot corner-delay extrapolation.

### 3.5 Active Learning

```bash
.venv/bin/python experiments/v2_active_learning.py
```

Expected outputs:

```text
results/v2_active_learning/v2_active_learning_results.csv
results/v2_active_learning/v2_active_learning_budget_comparison.csv
results/v2_active_learning/v2_active_learning_summary.csv
results/v2_active_learning/v2_active_learning_summary.json
results/v2_active_learning/v2_active_learning_report.md
results/v2_active_learning/v2_active_learning_curves.png
results/v2_active_learning/v2_active_learning_curves.pdf
```

The active-learning experiment is retrospective. It treats the existing SPICE rows as an oracle-backed pool and does not claim that new SPICE simulations were run adaptively.

### 3.6 Diagnostics and Candidate Verification

```bash
.venv/bin/python experiments/v2_model_diagnostics.py
```

Expected outputs:

```text
results/v2_diagnostics/v2_holdout_metrics.csv
results/v2_diagnostics/v2_error_by_cell.csv
results/v2_diagnostics/v2_predictions_holdout.csv
results/v2_diagnostics/v2_pareto_selected_candidates.csv
results/v2_diagnostics/v2_diagnostics_summary.json
results/v2_diagnostics/v2_diagnostics_report.md
results/v2_diagnostics/v2_predicted_vs_spice.png
results/v2_diagnostics/v2_predicted_vs_spice.pdf
results/v2_diagnostics/v2_error_by_cell.png
results/v2_diagnostics/v2_error_by_cell.pdf
results/v2_diagnostics/v2_spice_verified_pareto_case.png
results/v2_diagnostics/v2_spice_verified_pareto_case.pdf
```

The candidate-selection study is held-out SPICE-pool verification. It is not a new sign-off optimization run.

## 4. Manuscript Figures

The manuscript figure files are under:

```text
manuscript/figures/
```

Figure mapping:

| Manuscript figure | File |
|---|---|
| Fig. 1 Workflow | `fig1_workflow.pdf` |
| Fig. 2 Predicted vs SPICE | `fig2_predicted_vs_spice.pdf` |
| Fig. 3 Error by cell | `fig3_error_by_cell.pdf` |
| Fig. 4 Few-shot transfer | `fig4_fewshot_transfer_curves.pdf` |
| Fig. 5 Active learning | `fig5_active_learning_curves.pdf` |
| Fig. 6 Candidate verification | `fig6_spice_verified_pareto_case.pdf` |

Regenerate Fig. 1:

```bash
.venv/bin/python experiments/plot_workflow_figure.py
```

The other manuscript figures are derived from the V2 result folders listed above.

## 5. Manuscript Build

Build the Elsevier LaTeX manuscript from `manuscript/`:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error microelectronics_journal_submission.tex
```

Expected output:

```text
manuscript/microelectronics_journal_submission.pdf
```

The latest checked build should be regenerated after manuscript edits and checked for undefined citations, empty-year BibTeX warnings, and rerun-required cross-reference warnings.

## 6. Files Not Used as Publication Evidence

Files from the earlier inverter-only project and exploratory analyses are separated under `previous_work/`. These should not be used as Microelectronics Journal evidence unless explicitly audited:

- `previous_work/chinese_manuscript/`: prior Chinese manuscript material.
- `previous_work/legacy_data_and_scripts/dataset_hybrid_combined.csv`: legacy 155-row inverter dataset.
- `previous_work/legacy_data_and_scripts/`: legacy scripts such as `cross_cell_real_spice.py`.
- `previous_work/legacy_results/`: older exploratory figures and reports.

The source-aware ablation uses the legacy 155-row dataset only as a low-fidelity negative-control source.

## 7. Claim Boundaries

When reusing the data or scripts, preserve the following boundaries:

- The surrogate supports early design-space exploration.
- Final design points require SPICE re-validation.
- The current templates are controlled transistor-level arcs, not full Liberty timing/power characterization.
- The datasets do not exhaustively cover all PVT corners, load/slew combinations, timing arcs, leakage states, or layout parasitics.
- The legacy 155-row inverter dataset is not SPICE-equivalent publication evidence.

## 8. Suggested Supplementary Archive Contents

For review or public archiving, include:

```text
README.md
REPRODUCIBILITY.md
data/dataset_v2_spice_320.csv
data/dataset_v3_spice_480.csv
spice_v2/generate_spice_dataset.py
spice_v2/README.md
spice_v2/schema.md
spice_v2/status.md
experiments/
results/v2/
results/source_aware/
results/v2_active_learning/
results/v2_diagnostics/
results/v2_robustness/
results/v3_robustness/
results/v3_scale_validation/
manuscript/figures/
```

Do not redistribute GF180MCU PDK model files unless the license permits it. Instead, document where users can obtain the PDK and provide the model path expected by the scripts.

## 9. Standalone Supplementary Archive Builder

For Editorial Manager upload, generate a separate data/code supplement with:

```bash
python3 tools/prepare_supplementary_archive.py
```

Default output:

```text
supplementary_archive/mej_reproducibility_supplement/
supplementary_archive/mej_reproducibility_supplement.zip
```

The directory includes a `SUPPLEMENT_README.md` and `CHECKSUMS.sha256`. The readiness checker validates the supplement directory, zip, exclusions, and checksums.
