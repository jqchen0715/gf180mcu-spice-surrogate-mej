# SPICE V2 Pipeline Status

Last updated: 2026-06-02

## What Works

- `ngspice` is available locally.
- `spice_v2/generate_spice_dataset.py` can generate transistor-level netlists for:
  - `INV`
  - `NAND2`
  - `NOR2`
  - `XOR2`
- The script can call `ngspice -b`.
- The script can parse `.measure` outputs:
  - `tphl`
  - `tplh`
  - `i_vdd_avg`
  - `power_avg_uW`
- Debug CSV output is generated with explicit provenance fields.
- Real GF180MCU model files are now available after initializing the required submodules.
- A real seed dataset has been generated at `data/dataset_v2_spice_seed.csv`.
- A four-cell manuscript seed dataset has been generated at `data/dataset_v2_spice_320.csv`.
- An independent four-cell validation dataset has been generated at `data/dataset_v3_spice_480.csv`.
- A first baseline/transfer benchmark has been generated under `results/v2/`.
- A first source-aware fusion ablation has been generated under `results/source_aware/`.
- A first active-learning sample-efficiency study has been generated under `results/v2_active_learning/`.
- A first diagnostics and SPICE-verified candidate-selection case study has been generated under `results/v2_diagnostics/`.
- V3 scale-up robustness has been generated under `results/v3_robustness/`.
- V2-to-V3 external validation and corner-support calibration have been generated under `results/v3_scale_validation/`.

Validated command:

```bash
.venv/bin/python spice_v2/generate_spice_dataset.py \
  --samples-per-cell 1 \
  --allow-generic-debug-models \
  --output data/dataset_v2_debug_generic.csv
```

Validation result:

- 3 rows generated.
- All rows have `status=ok`.
- All rows are marked `fidelity=GenericDebug_NotForPublication`.

## Real SPICE Seed Dataset

Generated command:

```bash
.venv/bin/python spice_v2/generate_spice_dataset.py \
  --samples-per-cell 30 \
  --output data/dataset_v2_spice_seed.csv
```

Current result:

- 90 rows total.
- 30 `INV`, 30 `NAND2`, 30 `NOR2`.
- 10 rows per `typical`, `ss`, and `ff` corner for each cell.
- 90 rows have `status=ok`.
- 90 rows have `fidelity=SPICE_GF180MCU`.
- Each row records the ngspice log path.

Measured output ranges:

| Cell | Delay avg range (ns) | Mean delay (ns) | Power range (uW) | Mean power (uW) |
|---|---:|---:|---:|---:|
| INV | 0.0529-0.5440 | 0.2276 | 0.9298-10.2381 | 5.6087 |
| NAND2 | 0.0567-0.6297 | 0.2688 | 0.9581-11.8578 | 6.2373 |
| NOR2 | 0.1036-1.6791 | 0.3363 | 1.0099-11.9219 | 6.1551 |

## Four-Cell SPICE Dataset

Generated command:

```bash
.venv/bin/python spice_v2/generate_spice_dataset.py \
  --cells INV NAND2 NOR2 XOR2 \
  --samples-per-cell 80 \
  --output data/dataset_v2_spice_320.csv
```

Current result:

- 320 rows total.
- 80 rows each for `INV`, `NAND2`, `NOR2`, and `XOR2`.
- 26 `ff`, 27 `ss`, and 27 `typical` rows per cell.
- 320 rows have `status=ok`.
- 320 rows have `fidelity=SPICE_GF180MCU`.
- Each row records the generated netlist and ngspice log path.

Measured output ranges:

| Cell | Delay avg range (ns) | Mean delay (ns) | Power range (uW) | Mean power (uW) |
|---|---:|---:|---:|---:|
| INV | 0.0642-0.7893 | 0.2517 | 0.4587-11.2254 | 5.5114 |
| NAND2 | 0.0572-1.6593 | 0.2844 | 0.4854-11.9225 | 6.2410 |
| NOR2 | 0.0734-1.2820 | 0.3350 | 0.8304-12.0894 | 6.2119 |
| XOR2 | 0.1530-1.2794 | 0.3844 | 1.7382-15.7036 | 8.0312 |

The current `XOR2` implementation is a transistor-level XOR arc with `A2` held high and `A1` toggled, so the measured output is an inverter-like arc through the XOR topology. The manuscript should describe it as a controlled single-input timing arc rather than full Liberty characterization.

## V3 Independent Validation Dataset

Generated command:

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

Current result:

- 480 rows total.
- 120 rows each for `INV`, `NAND2`, `NOR2`, and `XOR2`.
- 160 rows each for `ff`, `ss`, and `typical`.
- 40 rows per cell-corner pair.
- 480 rows have `status=ok`.
- 480 rows have `fidelity=SPICE_GF180MCU`.
- Each row records a generated netlist path and ngspice log path in separate V3 provenance directories.

Measured output ranges:

| Quantity | Range / mean |
|---|---:|
| `Wn_um` | 0.5282-4.9884, mean 2.7512 |
| `Wp_Wn_ratio` | 1.5029-2.9993, mean 2.2500 |
| `Vdd` | 1.6207-1.9799 V, mean 1.7999 V |
| `Temp` | -19.9230-99.8525 degC, mean 40.0051 degC |
| `Cload_fF` | 1.0660-99.7811 fF, mean 50.5055 fF |
| `slew_ps` | 10.6724-498.6520 ps, mean 254.9560 ps |
| `delay_avg_ns` | 0.0354-1.8656 ns, mean 0.3191 ns |
| `power_avg_uW` | 0.4893-17.6729 uW, mean 6.5122 uW |

## Baseline and Transfer Benchmark

Generated command:

```bash
.venv/bin/python experiments/v2_baseline_transfer.py \
  --dataset data/dataset_v2_spice_320.csv
```

Current result:

- Results CSV: `results/v2/v2_baseline_transfer_results.csv`.
- Summary report: `results/v2/v2_baseline_transfer_report.md`.
- Few-shot curve figure: `results/v2/v2_fewshot_transfer_curves.png`.
- Few-shot curve PDF: `results/v2/v2_fewshot_transfer_curves.pdf`.
- Random 80/20 split best model: Gradient Boosting.
- Best random-split delay result: R2 = 0.8708, MAE = 0.0483 ns.
- Best random-split power result: R2 = 0.9696, MAE = 0.4372 uW.
- Leave-one-cell-out transfer is evaluated for k = 0, 5, 10, 20, and 40 target-cell support samples.
- From-scratch few-shot baselines are evaluated for k = 5, 10, 20, and 40.
- Median best-model transfer R2 improves from 0.7365 to 0.8807 for delay and from 0.8966 to 0.9807 for power when moving from zero-shot to 40-shot.
- At k = 40, transfer remains better than from-scratch few-shot learning by median R2 gains of 0.3324 for delay and 0.0815 for power.

## Source-Aware Fusion Ablation

Generated command:

```bash
.venv/bin/python experiments/source_aware_ablation.py
```

Current result:

- Results CSV: `results/source_aware/source_aware_ablation_results.csv`.
- Summary CSV: `results/source_aware/source_aware_ablation_summary.csv`.
- Summary report: `results/source_aware/source_aware_ablation_report.md`.
- High-fidelity target source: 80 V2 `INV` rows from `data/dataset_v2_spice_320.csv`.
- Low-fidelity auxiliary source: 155 legacy inverter rows from `previous_work/legacy_data_and_scripts/dataset_hybrid_combined.csv`.
- Common feature space: `Wn_um`, `Vdd`, and `Temp`.
- Main conclusion: the legacy 155-row data should not be naively merged into the V2 SPICE dataset. For GradientBoosting delay prediction, HF-only median R2 = 0.1966, naive merge median R2 = -0.9201, 1.5x weighted merge median R2 = -1.3062, and LF-only median R2 = -303.7342.

## Active-Learning Sample-Efficiency Study

Generated command:

```bash
.venv/bin/python experiments/v2_active_learning.py
```

Current result:

- Results CSV: `results/v2_active_learning/v2_active_learning_results.csv`.
- Budget comparison CSV: `results/v2_active_learning/v2_active_learning_budget_comparison.csv`.
- Summary report: `results/v2_active_learning/v2_active_learning_report.md`.
- Curve figure: `results/v2_active_learning/v2_active_learning_curves.png`.
- Curve PDF: `results/v2_active_learning/v2_active_learning_curves.pdf`.
- Protocol: pool-based acquisition from the 320 V2 SPICE rows, initial 20 labels, batch size 20, RandomForestRegressor, five random seeds.
- Main conclusion: uncertainty-guided sampling is not uniformly better at very low budgets, where random coverage is strong. At 200 labeled rows, uncertainty improves median R2 from 0.7594 to 0.7705 for delay and from 0.9077 to 0.9218 for power; the hybrid random-then-uncertainty strategy gives the best delay median R2 at 0.7826.

## Diagnostics and SPICE-Verified Candidate Selection

Generated command:

```bash
.venv/bin/python experiments/v2_model_diagnostics.py
```

Current result:

- Report: `results/v2_diagnostics/v2_diagnostics_report.md`.
- Held-out predictions: `results/v2_diagnostics/v2_predictions_holdout.csv`.
- Held-out metrics: `results/v2_diagnostics/v2_holdout_metrics.csv`.
- Error by cell: `results/v2_diagnostics/v2_error_by_cell.csv`.
- Surrogate-selected candidates: `results/v2_diagnostics/v2_pareto_selected_candidates.csv`.
- Figures:
  - `results/v2_diagnostics/v2_predicted_vs_spice.png`.
  - `results/v2_diagnostics/v2_error_by_cell.png`.
  - `results/v2_diagnostics/v2_spice_verified_pareto_case.png`.
- Held-out random-split metrics reproduce the baseline result: delay R2 = 0.8708, MAE = 0.0483 ns; power R2 = 0.9696, MAE = 0.4372 uW.
- In the retrospective candidate-selection case, the surrogate selects 12 held-out candidates using a normalized predicted delay-power score; 7 are in the actual SPICE top 10%, and 11 are in the actual SPICE top 20%.

## V3 Scale-Up Robustness

Generated command:

```bash
.venv/bin/python experiments/v2_robustness_ablation.py \
  --dataset data/dataset_v3_spice_480.csv \
  --outdir results/v3_robustness \
  --output-prefix v3 \
  --learning-curve-rows 40 80 120 160 240 320 384
```

Current result:

- Report: `results/v3_robustness/v3_robustness_report.md`.
- Repeated random-split delay: best median model is `SVR_RBF`, R2 = 0.9099.
- Repeated random-split power: best median model is `MLP`, R2 = 0.9895.
- Gradient boosting remains consistent: median R2 = 0.8792 for delay and 0.9745 for power.
- Leave-one-corner-out remains the main stress case for delay: ff delay R2 = 0.2406, ss delay R2 = 0.5646, typical delay R2 = 0.8478.

## V2-to-V3 External Validation and Corner Support

Generated command:

```bash
.venv/bin/python experiments/v3_scale_and_corner_support.py
```

Current result:

- Report: `results/v3_scale_validation/v3_scale_validation_report.md`.
- V2-trained gradient boosting evaluated on all V3 rows: delay R2 = 0.8907, power R2 = 0.9749.
- V2-trained MLP evaluated on all V3 rows: power R2 = 0.9878.
- V2-trained V3 candidate ranking selects 24 candidates; 24/24 are actual SPICE top-20% points.
- ff-corner delay support curve: R2 = 0.1645 with zero support, then 0.6373, 0.7641, and 0.8167 with 12, 24, and 48 same-corner support rows.

Simulation variable ranges:

- `Wn_um`: 0.5174-4.9905 um.
- `Wp_Wn_ratio`: 1.5047-2.9978.
- `Vdd`: 1.6200-1.9773 V.
- `Temp`: -19.9713-99.9953 degC.
- `Cload_fF`: 1.2712-99.8324 fF.
- `slew_ps`: 10.8686-499.4545 ps.
- `L_um`: 0.28 um.

Prerequisite check command:

```bash
.venv/bin/python spice_v2/generate_spice_dataset.py --check-only
```

Current result:

- Finds `/opt/homebrew/bin/ngspice`.
- Finds `gf180mcu-pdk/libraries/gf180mcu_fd_pr/latest/models/ngspice/sm141064.ngspice`.
- Reports that prerequisites are available for real GF180MCU ngspice generation.

## Current Manuscript Boundary

Use `data/dataset_v2_spice_320.csv` as the primary SPICE-grounded dataset and `data/dataset_v3_spice_480.csv` as an independent validation dataset. The manuscript should still avoid claiming sign-off replacement, full Liberty characterization, complete timing-arc coverage, layout parasitic extraction, or a justified fixed 1.5x source weight.
