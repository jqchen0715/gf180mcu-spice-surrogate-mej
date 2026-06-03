# V2 Robustness and Ablation Report

## Dataset

- Rows used: 320 publication-eligible GF180MCU/ngspice rows.
- Cells: INV, NAND2, NOR2, XOR2.
- Targets: `delay_avg_ns` and `power_avg_uW`.
- All experiments use only the new V2 SPICE dataset; no legacy data are used.

## Repeated Random-Split Model Zoo

Top four models per target by median R2 across repeated stratified splits:

| target | model | runs | median_r2 | q25_r2 | q75_r2 | min_r2 | median_mae | median_mape_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| delay_avg_ns | GradientBoosting | 20.0000 | 0.8807 | 0.8588 | 0.9000 | 0.7895 | 0.0475 | 14.3907 |
| delay_avg_ns | ExtraTrees | 20.0000 | 0.8644 | 0.8171 | 0.8839 | 0.7748 | 0.0496 | 16.8672 |
| delay_avg_ns | HistGradientBoosting | 20.0000 | 0.8542 | 0.8400 | 0.8686 | 0.6776 | 0.0495 | 15.2366 |
| delay_avg_ns | SVR_RBF | 20.0000 | 0.8319 | 0.8044 | 0.8614 | 0.7253 | 0.0541 | 19.5941 |
| power_avg_uW | MLP | 20.0000 | 0.9819 | 0.9704 | 0.9866 | 0.9531 | 0.3323 | 8.2586 |
| power_avg_uW | HistGradientBoosting | 20.0000 | 0.9793 | 0.9750 | 0.9802 | 0.9606 | 0.3552 | 6.9757 |
| power_avg_uW | SVR_RBF | 20.0000 | 0.9779 | 0.9740 | 0.9809 | 0.9596 | 0.3503 | 9.0190 |
| power_avg_uW | GradientBoosting | 20.0000 | 0.9718 | 0.9643 | 0.9763 | 0.9593 | 0.3930 | 7.2068 |

## Gradient-Boosting Feature Ablation

| target | feature_set | runs | median_r2 | q25_r2 | q75_r2 | median_mae | median_mape_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| delay_avg_ns | full | 20.0000 | 0.8807 | 0.8588 | 0.9000 | 0.0475 | 14.3907 |
| delay_avg_ns | no_cell_or_arc | 20.0000 | 0.8041 | 0.7665 | 0.8361 | 0.0689 | 24.1826 |
| delay_avg_ns | no_corner | 20.0000 | 0.7550 | 0.7066 | 0.7949 | 0.0742 | 25.9472 |
| delay_avg_ns | no_load_slew | 20.0000 | 0.4184 | 0.2792 | 0.4967 | 0.1165 | 41.7936 |
| delay_avg_ns | sizing_pvt_only | 20.0000 | 0.2074 | 0.0031 | 0.3299 | 0.1320 | 50.6762 |
| power_avg_uW | no_corner | 20.0000 | 0.9718 | 0.9651 | 0.9770 | 0.3936 | 7.3020 |
| power_avg_uW | full | 20.0000 | 0.9718 | 0.9643 | 0.9763 | 0.3930 | 7.2068 |
| power_avg_uW | no_cell_or_arc | 20.0000 | 0.8306 | 0.8069 | 0.8514 | 0.9810 | 18.6927 |
| power_avg_uW | no_load_slew | 20.0000 | 0.1379 | 0.0760 | 0.1904 | 2.4414 | 62.4199 |
| power_avg_uW | sizing_pvt_only | 20.0000 | 0.0157 | -0.1213 | 0.0993 | 2.5460 | 63.3870 |

## Gradient-Boosting Learning Curve

| target | train_rows | runs | median_r2 | q25_r2 | q75_r2 | median_mae | median_mape_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| delay_avg_ns | 40.0000 | 20.0000 | 0.5314 | 0.4170 | 0.6019 | 0.0997 | 33.2718 |
| delay_avg_ns | 80.0000 | 20.0000 | 0.6644 | 0.6284 | 0.7521 | 0.0738 | 23.1987 |
| delay_avg_ns | 120.0000 | 20.0000 | 0.7804 | 0.7250 | 0.8016 | 0.0607 | 18.7997 |
| delay_avg_ns | 160.0000 | 20.0000 | 0.8306 | 0.7771 | 0.8491 | 0.0539 | 17.4841 |
| delay_avg_ns | 220.0000 | 20.0000 | 0.8713 | 0.8428 | 0.8950 | 0.0470 | 14.8419 |
| delay_avg_ns | 256.0000 | 20.0000 | 0.8807 | 0.8588 | 0.9000 | 0.0475 | 14.3907 |
| power_avg_uW | 40.0000 | 20.0000 | 0.8078 | 0.7754 | 0.8507 | 1.0500 | 20.8642 |
| power_avg_uW | 80.0000 | 20.0000 | 0.9055 | 0.8962 | 0.9135 | 0.7348 | 14.3907 |
| power_avg_uW | 120.0000 | 20.0000 | 0.9429 | 0.9279 | 0.9493 | 0.5746 | 11.4360 |
| power_avg_uW | 160.0000 | 20.0000 | 0.9511 | 0.9415 | 0.9569 | 0.5284 | 10.4171 |
| power_avg_uW | 220.0000 | 20.0000 | 0.9642 | 0.9604 | 0.9701 | 0.4312 | 8.4765 |
| power_avg_uW | 256.0000 | 20.0000 | 0.9718 | 0.9643 | 0.9763 | 0.3930 | 7.2068 |

## Leave-One-Corner-Out Stress Test

| target | feature_set | heldout_corner | runs | median_r2 | median_mae | median_mape_pct |
| --- | --- | --- | --- | --- | --- | --- |
| delay_avg_ns | full | ff | 1.0000 | 0.1178 | 0.1106 | 50.9885 |
| delay_avg_ns | full | ss | 1.0000 | 0.5420 | 0.1375 | 29.6162 |
| delay_avg_ns | full | typical | 1.0000 | 0.8432 | 0.0492 | 23.1887 |
| delay_avg_ns | no_corner | ff | 1.0000 | -0.1061 | 0.1234 | 56.0339 |
| delay_avg_ns | no_corner | ss | 1.0000 | 0.5014 | 0.1423 | 30.1119 |
| delay_avg_ns | no_corner | typical | 1.0000 | 0.8678 | 0.0458 | 20.3623 |
| power_avg_uW | full | ff | 1.0000 | 0.9715 | 0.4303 | 8.4234 |
| power_avg_uW | full | ss | 1.0000 | 0.9674 | 0.4343 | 8.0489 |
| power_avg_uW | full | typical | 1.0000 | 0.9720 | 0.3574 | 8.5676 |
| power_avg_uW | no_corner | ff | 1.0000 | 0.9715 | 0.4309 | 8.4133 |
| power_avg_uW | no_corner | ss | 1.0000 | 0.9673 | 0.4367 | 8.0702 |
| power_avg_uW | no_corner | typical | 1.0000 | 0.9713 | 0.3615 | 8.4275 |

## Repeated Leave-One-Cell-Out Transfer

| target | training_protocol | fewshot_k | runs | median_r2 | min_r2 | median_mae | median_mape_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| delay_avg_ns | source_plus_target_support | 0.0000 | 80.0000 | 0.7481 | 0.1652 | 0.0857 | 27.0317 |
| delay_avg_ns | source_plus_target_support | 20.0000 | 80.0000 | 0.8440 | 0.3998 | 0.0572 | 16.9114 |
| delay_avg_ns | source_plus_target_support | 40.0000 | 80.0000 | 0.8603 | 0.4756 | 0.0501 | 15.5631 |
| delay_avg_ns | target_support_only | 20.0000 | 80.0000 | 0.2723 | -3.7069 | 0.1204 | 40.1458 |
| delay_avg_ns | target_support_only | 40.0000 | 80.0000 | 0.5321 | -3.4968 | 0.0880 | 30.0498 |
| power_avg_uW | source_plus_target_support | 0.0000 | 80.0000 | 0.8575 | 0.5260 | 0.7526 | 15.8935 |
| power_avg_uW | source_plus_target_support | 20.0000 | 80.0000 | 0.9708 | 0.8149 | 0.3688 | 8.7791 |
| power_avg_uW | source_plus_target_support | 40.0000 | 80.0000 | 0.9755 | 0.8459 | 0.3571 | 7.9458 |
| power_avg_uW | target_support_only | 20.0000 | 80.0000 | 0.8345 | 0.5809 | 0.9727 | 23.0146 |
| power_avg_uW | target_support_only | 40.0000 | 80.0000 | 0.9124 | 0.8009 | 0.7000 | 15.6006 |

## Candidate-Ranking Enrichment

| selection | runs | median_top10_hits | median_top20_hits | median_actual_rank | median_actual_score | median_spearman | empirical_p_top10_ge_surrogate | empirical_p_top20_ge_surrogate | empirical_p_rank_le_surrogate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| random_selection | 10000.0000 | 1.0000 | 2.0000 | 32.5000 | 0.3099 | 0.9774 |  |  |  |
| surrogate_top_score | 20.0000 | 7.0000 | 11.0000 | 6.5000 | 0.0907 | 0.9774 | 0.0 | 0.0 | 0.0 |

## Output Files

- `v2_model_zoo_repeated.csv` and summary
- `v2_feature_ablation.csv` and summary
- `v2_learning_curve.csv` and summary
- `v2_corner_holdout.csv` and summary
- `v2_transfer_robustness.csv` and summary
- `v2_candidate_ranking_robustness.csv` and summary
