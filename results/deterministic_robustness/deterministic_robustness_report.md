# DETERMINISTIC Robustness and Ablation Report

## Dataset

- Rows used: 320 publication-eligible GF180MCU/ngspice rows.
- Cells: INV, NAND2, NOR2, XOR2.
- Targets: `delay_avg_ns` and `power_avg_uW`.
- All experiments use only the DETERMINISTIC SPICE dataset; no legacy data are used.

## Repeated Random-Split Model Zoo

Top four models per target by median R2 across repeated stratified splits:

| target | model | runs | median_r2 | q25_r2 | q75_r2 | min_r2 | median_mae | median_mape_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| delay_avg_ns | GradientBoosting | 20.0000 | 0.8803 | 0.8659 | 0.9082 | 0.7902 | 0.0462 | 13.8289 |
| delay_avg_ns | ExtraTrees | 20.0000 | 0.8690 | 0.8158 | 0.8880 | 0.7595 | 0.0499 | 16.7440 |
| delay_avg_ns | HistGradientBoosting | 20.0000 | 0.8496 | 0.8282 | 0.8671 | 0.6898 | 0.0500 | 15.5870 |
| delay_avg_ns | SVR_RBF | 20.0000 | 0.8347 | 0.8041 | 0.8670 | 0.7264 | 0.0533 | 19.3502 |
| power_avg_uW | MLP | 20.0000 | 0.9808 | 0.9704 | 0.9866 | 0.9531 | 0.3417 | 8.2639 |
| power_avg_uW | HistGradientBoosting | 20.0000 | 0.9784 | 0.9757 | 0.9805 | 0.9600 | 0.3532 | 7.2849 |
| power_avg_uW | SVR_RBF | 20.0000 | 0.9779 | 0.9740 | 0.9810 | 0.9596 | 0.3496 | 9.0161 |
| power_avg_uW | GradientBoosting | 20.0000 | 0.9721 | 0.9657 | 0.9775 | 0.9583 | 0.3883 | 7.5661 |

## Gradient-Boosting Feature Ablation

| target | feature_set | runs | median_r2 | q25_r2 | q75_r2 | median_mae | median_mape_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| delay_avg_ns | full | 20.0000 | 0.8803 | 0.8659 | 0.9082 | 0.0462 | 13.8289 |
| delay_avg_ns | no_cell_or_arc | 20.0000 | 0.8009 | 0.7603 | 0.8395 | 0.0682 | 24.4521 |
| delay_avg_ns | no_corner | 20.0000 | 0.7447 | 0.7002 | 0.8016 | 0.0729 | 25.3657 |
| delay_avg_ns | no_load_slew | 20.0000 | 0.4261 | 0.2779 | 0.4803 | 0.1155 | 41.4186 |
| delay_avg_ns | sizing_pvt_only | 20.0000 | 0.2113 | -0.0004 | 0.3366 | 0.1310 | 51.3808 |
| power_avg_uW | no_corner | 20.0000 | 0.9722 | 0.9650 | 0.9774 | 0.3894 | 7.5048 |
| power_avg_uW | full | 20.0000 | 0.9721 | 0.9657 | 0.9775 | 0.3883 | 7.5661 |
| power_avg_uW | no_cell_or_arc | 20.0000 | 0.8299 | 0.8119 | 0.8446 | 0.9808 | 18.5901 |
| power_avg_uW | no_load_slew | 20.0000 | 0.1454 | 0.0504 | 0.2139 | 2.4190 | 61.3067 |
| power_avg_uW | sizing_pvt_only | 20.0000 | 0.0066 | -0.1276 | 0.0986 | 2.5683 | 62.5630 |

## Gradient-Boosting Learning Curve

| target | train_rows | runs | median_r2 | q25_r2 | q75_r2 | median_mae | median_mape_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| delay_avg_ns | 40.0000 | 20.0000 | 0.4861 | 0.3957 | 0.5718 | 0.0991 | 32.6506 |
| delay_avg_ns | 80.0000 | 20.0000 | 0.6790 | 0.6348 | 0.7475 | 0.0751 | 23.0165 |
| delay_avg_ns | 120.0000 | 20.0000 | 0.7838 | 0.6869 | 0.8169 | 0.0599 | 18.4409 |
| delay_avg_ns | 160.0000 | 20.0000 | 0.8201 | 0.7950 | 0.8527 | 0.0553 | 17.1062 |
| delay_avg_ns | 220.0000 | 20.0000 | 0.8667 | 0.8464 | 0.8971 | 0.0458 | 14.5875 |
| delay_avg_ns | 256.0000 | 20.0000 | 0.8803 | 0.8659 | 0.9082 | 0.0462 | 13.8289 |
| power_avg_uW | 40.0000 | 20.0000 | 0.8045 | 0.7764 | 0.8480 | 1.0444 | 20.7605 |
| power_avg_uW | 80.0000 | 20.0000 | 0.9014 | 0.8959 | 0.9179 | 0.7301 | 14.3440 |
| power_avg_uW | 120.0000 | 20.0000 | 0.9424 | 0.9266 | 0.9497 | 0.5797 | 11.1551 |
| power_avg_uW | 160.0000 | 20.0000 | 0.9509 | 0.9437 | 0.9587 | 0.5306 | 10.5277 |
| power_avg_uW | 220.0000 | 20.0000 | 0.9647 | 0.9616 | 0.9697 | 0.4429 | 8.4278 |
| power_avg_uW | 256.0000 | 20.0000 | 0.9721 | 0.9657 | 0.9775 | 0.3883 | 7.5661 |

## Leave-One-Corner-Out Stress Test

| target | feature_set | heldout_corner | runs | median_r2 | median_mae | median_mape_pct |
| --- | --- | --- | --- | --- | --- | --- |
| delay_avg_ns | full | ff | 1.0000 | -0.1798 | 0.1336 | 63.2040 |
| delay_avg_ns | full | ss | 1.0000 | 0.5113 | 0.1422 | 30.1047 |
| delay_avg_ns | full | typical | 1.0000 | 0.8388 | 0.0501 | 22.4606 |
| delay_avg_ns | no_corner | ff | 1.0000 | -0.0430 | 0.1204 | 54.7779 |
| delay_avg_ns | no_corner | ss | 1.0000 | 0.5263 | 0.1412 | 30.1564 |
| delay_avg_ns | no_corner | typical | 1.0000 | 0.8451 | 0.0512 | 22.7896 |
| power_avg_uW | full | ff | 1.0000 | 0.9698 | 0.4314 | 8.4373 |
| power_avg_uW | full | ss | 1.0000 | 0.9643 | 0.4591 | 8.1440 |
| power_avg_uW | full | typical | 1.0000 | 0.9744 | 0.3368 | 8.1613 |
| power_avg_uW | no_corner | ff | 1.0000 | 0.9703 | 0.4285 | 8.3875 |
| power_avg_uW | no_corner | ss | 1.0000 | 0.9639 | 0.4627 | 8.1800 |
| power_avg_uW | no_corner | typical | 1.0000 | 0.9743 | 0.3377 | 8.1805 |

## Repeated Leave-One-Cell-Out Transfer

| target | training_protocol | fewshot_k | runs | median_r2 | min_r2 | median_mae | median_mape_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| delay_avg_ns | source_plus_target_support | 0.0000 | 80.0000 | 0.7561 | 0.2133 | 0.0858 | 26.9385 |
| delay_avg_ns | source_plus_target_support | 20.0000 | 80.0000 | 0.8467 | 0.3852 | 0.0558 | 16.8717 |
| delay_avg_ns | source_plus_target_support | 40.0000 | 80.0000 | 0.8644 | 0.5729 | 0.0487 | 15.1138 |
| delay_avg_ns | target_support_only | 20.0000 | 80.0000 | 0.2774 | -3.9731 | 0.1200 | 40.3813 |
| delay_avg_ns | target_support_only | 40.0000 | 80.0000 | 0.5361 | -3.4888 | 0.0905 | 29.8399 |
| power_avg_uW | source_plus_target_support | 0.0000 | 80.0000 | 0.8442 | 0.5281 | 0.7762 | 15.8663 |
| power_avg_uW | source_plus_target_support | 20.0000 | 80.0000 | 0.9720 | 0.8155 | 0.3680 | 8.1658 |
| power_avg_uW | source_plus_target_support | 40.0000 | 80.0000 | 0.9743 | 0.8350 | 0.3555 | 8.0230 |
| power_avg_uW | target_support_only | 20.0000 | 80.0000 | 0.8340 | 0.5894 | 0.9705 | 23.0591 |
| power_avg_uW | target_support_only | 40.0000 | 80.0000 | 0.9123 | 0.7917 | 0.6908 | 15.7638 |

## Candidate-Ranking Enrichment

| selection | runs | median_top10_hits | median_top20_hits | median_actual_rank | median_actual_score | median_spearman | empirical_p_top10_ge_surrogate | empirical_p_top20_ge_surrogate | empirical_p_rank_le_surrogate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| random_selection | 10000.0000 | 1.0000 | 2.0000 | 32.5000 | 0.3097 | 0.9785 |  |  |  |
| surrogate_top_score | 20.0000 | 7.0000 | 11.0000 | 6.5000 | 0.0906 | 0.9785 | 0.0 | 0.0 | 0.0 |

## Output Files

- `deterministic_model_zoo_repeated.csv` and summary
- `deterministic_feature_ablation.csv` and summary
- `deterministic_learning_curve.csv` and summary
- `deterministic_corner_holdout.csv` and summary
- `deterministic_transfer_robustness.csv` and summary
- `deterministic_candidate_ranking_robustness.csv` and summary
