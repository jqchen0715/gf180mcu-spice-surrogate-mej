# Source-Aware Fusion Ablation Report

## Dataset

- High-fidelity target data: 80 V2 `INV` rows from GF180MCU/ngspice.
- Low-fidelity auxiliary data: 155 legacy inverter rows from `previous_work/legacy_data_and_scripts/dataset_hybrid_combined.csv`.
- Shared feature space for this ablation: `Wn_um`, `Vdd`, and `Temp`.
- Evaluation data: held-out high-fidelity V2 `INV` rows only.

## Best Protocols by Target and Model

| target | model | protocol | hf_weight | median_r2 | median_mae | median_mape_pct |
| --- | --- | --- | --- | --- | --- | --- |
| delay_ns | GradientBoosting | hf_only |  | 0.1966 | 0.1095 | 61.8721 |
| delay_ns | RandomForest | source_indicator_weighted | 3.0 | 0.3599 | 0.1018 | 62.3034 |
| power_uW | GradientBoosting | weighted_merge_no_source | 5.0 | -0.6087 | 2.6575 | 100.4109 |
| power_uW | RandomForest | hf_only |  | -0.3826 | 2.5345 | 98.0971 |

## GradientBoosting Protocol Summary

| target | protocol | hf_weight | median_r2 | median_mae | median_mape_pct |
| --- | --- | --- | --- | --- | --- |
| delay_ns | hf_only |  | 0.1966 | 0.1095 | 61.8721 |
| delay_ns | source_aware_validation_gate | selected | 0.0748 | 0.1182 | 61.8721 |
| delay_ns | source_indicator_equal_weight |  | -0.9168 | 0.1694 | 112.7367 |
| delay_ns | naive_merge_equal_weight |  | -0.9201 | 0.1696 | 112.6024 |
| delay_ns | weighted_merge_no_source | 1.0 | -0.9201 | 0.1696 | 112.6024 |
| delay_ns | weighted_merge_no_source | 2.0 | -1.0248 | 0.1823 | 111.1888 |
| delay_ns | weighted_merge_no_source | 1.5 | -1.3062 | 0.1868 | 121.4347 |
| delay_ns | weighted_merge_no_source | 5.0 | -1.4798 | 0.1480 | 92.0598 |
| delay_ns | source_indicator_weighted | 1.5 | -1.6576 | 0.1872 | 122.1046 |
| delay_ns | weighted_merge_no_source | 10.0 | -1.8348 | 0.1697 | 88.3955 |
| delay_ns | weighted_merge_no_source | 3.0 | -1.8364 | 0.1735 | 110.0219 |
| delay_ns | source_indicator_weighted | 3.0 | -2.0330 | 0.1701 | 106.8991 |
| delay_ns | two_stage_lf_plus_hf_residual |  | -12.4912 | 0.2929 | 145.2312 |
| delay_ns | lf_only |  | -303.7342 | 1.8193 | 944.1587 |
| power_uW | weighted_merge_no_source | 5.0 | -0.6087 | 2.6575 | 100.4109 |
| power_uW | hf_only |  | -0.6247 | 2.7342 | 98.6257 |
| power_uW | weighted_merge_no_source | 2.0 | -0.6631 | 2.7334 | 105.0277 |
| power_uW | weighted_merge_no_source | 10.0 | -0.6660 | 2.6907 | 99.9620 |
| power_uW | source_indicator_weighted | 1.5 | -0.7104 | 2.7292 | 101.0526 |
| power_uW | source_indicator_equal_weight |  | -0.7127 | 2.7634 | 103.0708 |
| power_uW | weighted_merge_no_source | 1.5 | -0.7198 | 2.7396 | 101.4994 |
| power_uW | source_indicator_weighted | 3.0 | -0.7226 | 2.7339 | 101.3247 |
| power_uW | naive_merge_equal_weight |  | -0.7342 | 2.8068 | 103.5115 |
| power_uW | weighted_merge_no_source | 1.0 | -0.7342 | 2.8068 | 103.5115 |
| power_uW | weighted_merge_no_source | 3.0 | -0.7412 | 2.7363 | 100.4639 |
| power_uW | source_aware_validation_gate | selected | -0.7465 | 2.7363 | 95.4679 |
| power_uW | two_stage_lf_plus_hf_residual |  | -0.8429 | 2.8698 | 100.9406 |
| power_uW | lf_only |  | -1.9139 | 3.3875 | 55.6916 |

## GradientBoosting Weight Sweep Without Source Indicator

| target | hf_weight | median_r2 | median_mae | median_mape_pct |
| --- | --- | --- | --- | --- |
| delay_ns | 1.0 | -0.9201 | 0.1696 | 112.6024 |
| delay_ns | 2.0 | -1.0248 | 0.1823 | 111.1888 |
| delay_ns | 1.5 | -1.3062 | 0.1868 | 121.4347 |
| delay_ns | 5.0 | -1.4798 | 0.1480 | 92.0598 |
| delay_ns | 10.0 | -1.8348 | 0.1697 | 88.3955 |
| delay_ns | 3.0 | -1.8364 | 0.1735 | 110.0219 |
| power_uW | 5.0 | -0.6087 | 2.6575 | 100.4109 |
| power_uW | 2.0 | -0.6631 | 2.7334 | 105.0277 |
| power_uW | 10.0 | -0.6660 | 2.6907 | 99.9620 |
| power_uW | 1.5 | -0.7198 | 2.7396 | 101.4994 |
| power_uW | 1.0 | -0.7342 | 2.8068 | 103.5115 |
| power_uW | 3.0 | -0.7412 | 2.7363 | 100.4639 |

## Source-Aware Validation Gate Selections

| target | model | selected_protocol | count |
| --- | --- | --- | --- |
| delay_ns | GradientBoosting | hf_only | 8.0000 |
| delay_ns | GradientBoosting | source_indicator_equal_weight | 1.0000 |
| delay_ns | GradientBoosting | source_indicator_weighted_1.5 | 1.0000 |
| delay_ns | RandomForest | hf_only | 7.0000 |
| delay_ns | RandomForest | weighted_merge_no_source_3.0 | 3.0000 |
| power_uW | GradientBoosting | weighted_merge_no_source_3.0 | 4.0000 |
| power_uW | GradientBoosting | hf_only | 2.0000 |
| power_uW | GradientBoosting | naive_merge_equal_weight | 1.0000 |
| power_uW | GradientBoosting | source_indicator_equal_weight | 1.0000 |
| power_uW | GradientBoosting | source_indicator_weighted_1.5 | 1.0000 |
| power_uW | GradientBoosting | weighted_merge_no_source_1.5 | 1.0000 |
| power_uW | RandomForest | naive_merge_equal_weight | 3.0000 |
| power_uW | RandomForest | hf_only | 2.0000 |
| power_uW | RandomForest | source_indicator_equal_weight | 2.0000 |
| power_uW | RandomForest | source_indicator_weighted_1.5 | 1.0000 |
| power_uW | RandomForest | weighted_merge_no_source_1.5 | 1.0000 |
| power_uW | RandomForest | weighted_merge_no_source_3.0 | 1.0000 |

## Interpretation Notes

- `lf_only` measures how poorly the legacy source transfers when used as if it were SPICE-equivalent.
- `naive_merge_equal_weight` tests the unsafe merge strategy from the preliminary manuscript.
- `weighted_merge_no_source` tests whether a fixed high-fidelity weight such as 1.5x is justified.
- `source_indicator_*` lets the regressor distinguish high- and low-fidelity rows.
- `two_stage_lf_plus_hf_residual` uses the low-fidelity model as a base trend and learns a high-fidelity residual.
- `source_aware_validation_gate` chooses whether to use the auxiliary source based on a held-out high-fidelity validation subset, preventing blind negative transfer.
