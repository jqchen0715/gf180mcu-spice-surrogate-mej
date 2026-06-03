# V3 Robustness and Ablation Report

## Dataset

- Rows used: 480 publication-eligible GF180MCU/ngspice rows.
- Cells: INV, NAND2, NOR2, XOR2.
- Targets: `delay_avg_ns` and `power_avg_uW`.
- All experiments use only the V3 SPICE dataset; no legacy data are used.

## Repeated Random-Split Model Zoo

Top four models per target by median R2 across repeated stratified splits:

| target | model | runs | median_r2 | q25_r2 | q75_r2 | min_r2 | median_mae | median_mape_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| delay_avg_ns | SVR_RBF | 20.0000 | 0.9099 | 0.8873 | 0.9324 | 0.8289 | 0.0493 | 16.3113 |
| delay_avg_ns | HistGradientBoosting | 20.0000 | 0.8980 | 0.8540 | 0.9097 | 0.8099 | 0.0467 | 14.7634 |
| delay_avg_ns | GradientBoosting | 20.0000 | 0.8792 | 0.8704 | 0.9076 | 0.7904 | 0.0491 | 14.0153 |
| delay_avg_ns | MLP | 20.0000 | 0.8646 | 0.8179 | 0.8771 | 0.6752 | 0.0683 | 24.1637 |
| power_avg_uW | MLP | 20.0000 | 0.9895 | 0.9872 | 0.9924 | 0.9781 | 0.2440 | 6.0929 |
| power_avg_uW | SVR_RBF | 20.0000 | 0.9855 | 0.9824 | 0.9883 | 0.9777 | 0.2536 | 6.7453 |
| power_avg_uW | HistGradientBoosting | 20.0000 | 0.9757 | 0.9727 | 0.9794 | 0.9621 | 0.3399 | 6.4422 |
| power_avg_uW | GradientBoosting | 20.0000 | 0.9745 | 0.9707 | 0.9763 | 0.9602 | 0.3554 | 6.7510 |

## Gradient-Boosting Feature Ablation

| target | feature_set | runs | median_r2 | q25_r2 | q75_r2 | median_mae | median_mape_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| delay_avg_ns | full | 20.0000 | 0.8792 | 0.8704 | 0.9076 | 0.0491 | 14.0153 |
| delay_avg_ns | no_cell_or_arc | 20.0000 | 0.8199 | 0.8002 | 0.8413 | 0.0755 | 25.0397 |
| delay_avg_ns | no_corner | 20.0000 | 0.7638 | 0.7270 | 0.7906 | 0.0789 | 23.3044 |
| delay_avg_ns | no_load_slew | 20.0000 | 0.5719 | 0.5398 | 0.6278 | 0.1115 | 44.7708 |
| delay_avg_ns | sizing_pvt_only | 20.0000 | 0.3529 | 0.1825 | 0.3981 | 0.1413 | 62.1039 |
| power_avg_uW | no_corner | 20.0000 | 0.9747 | 0.9726 | 0.9766 | 0.3576 | 6.7133 |
| power_avg_uW | full | 20.0000 | 0.9745 | 0.9707 | 0.9763 | 0.3554 | 6.7510 |
| power_avg_uW | no_cell_or_arc | 20.0000 | 0.8334 | 0.8079 | 0.8365 | 0.9449 | 18.1574 |
| power_avg_uW | no_load_slew | 20.0000 | 0.0910 | 0.0299 | 0.1881 | 2.4825 | 63.9876 |
| power_avg_uW | sizing_pvt_only | 20.0000 | 0.0254 | -0.0828 | 0.0846 | 2.5732 | 68.5074 |

## Gradient-Boosting Learning Curve

| target | train_rows | runs | median_r2 | q25_r2 | q75_r2 | median_mae | median_mape_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| delay_avg_ns | 40.0000 | 20.0000 | 0.5240 | 0.4322 | 0.5655 | 0.1136 | 38.9710 |
| delay_avg_ns | 80.0000 | 20.0000 | 0.6448 | 0.5970 | 0.6836 | 0.0901 | 26.3218 |
| delay_avg_ns | 120.0000 | 20.0000 | 0.7518 | 0.7219 | 0.7892 | 0.0739 | 21.6260 |
| delay_avg_ns | 160.0000 | 20.0000 | 0.8230 | 0.7683 | 0.8625 | 0.0640 | 17.9529 |
| delay_avg_ns | 240.0000 | 20.0000 | 0.8619 | 0.8377 | 0.8843 | 0.0524 | 15.6027 |
| delay_avg_ns | 320.0000 | 20.0000 | 0.8795 | 0.8498 | 0.8952 | 0.0501 | 14.2812 |
| delay_avg_ns | 384.0000 | 20.0000 | 0.8792 | 0.8704 | 0.9076 | 0.0491 | 14.0153 |
| power_avg_uW | 40.0000 | 20.0000 | 0.7915 | 0.7548 | 0.8238 | 1.0695 | 23.2826 |
| power_avg_uW | 80.0000 | 20.0000 | 0.8949 | 0.8789 | 0.9095 | 0.7559 | 15.3484 |
| power_avg_uW | 120.0000 | 20.0000 | 0.9221 | 0.9126 | 0.9321 | 0.6393 | 12.8657 |
| power_avg_uW | 160.0000 | 20.0000 | 0.9440 | 0.9292 | 0.9499 | 0.5507 | 10.5854 |
| power_avg_uW | 240.0000 | 20.0000 | 0.9600 | 0.9556 | 0.9642 | 0.4401 | 8.4644 |
| power_avg_uW | 320.0000 | 20.0000 | 0.9702 | 0.9659 | 0.9725 | 0.3902 | 7.4873 |
| power_avg_uW | 384.0000 | 20.0000 | 0.9745 | 0.9707 | 0.9763 | 0.3554 | 6.7510 |

## Leave-One-Corner-Out Stress Test

| target | feature_set | heldout_corner | runs | median_r2 | median_mae | median_mape_pct |
| --- | --- | --- | --- | --- | --- | --- |
| delay_avg_ns | full | ff | 1.0000 | 0.2406 | 0.1169 | 55.7097 |
| delay_avg_ns | full | ss | 1.0000 | 0.5646 | 0.1410 | 28.2850 |
| delay_avg_ns | full | typical | 1.0000 | 0.8478 | 0.0476 | 19.9635 |
| delay_avg_ns | no_corner | ff | 1.0000 | -0.0438 | 0.1213 | 52.2338 |
| delay_avg_ns | no_corner | ss | 1.0000 | 0.5456 | 0.1440 | 28.7198 |
| delay_avg_ns | no_corner | typical | 1.0000 | 0.9015 | 0.0392 | 15.9293 |
| power_avg_uW | full | ff | 1.0000 | 0.9651 | 0.4217 | 9.1504 |
| power_avg_uW | full | ss | 1.0000 | 0.9753 | 0.3522 | 5.8883 |
| power_avg_uW | full | typical | 1.0000 | 0.9767 | 0.3481 | 7.0199 |
| power_avg_uW | no_corner | ff | 1.0000 | 0.9646 | 0.4197 | 9.0298 |
| power_avg_uW | no_corner | ss | 1.0000 | 0.9752 | 0.3521 | 5.8798 |
| power_avg_uW | no_corner | typical | 1.0000 | 0.9769 | 0.3394 | 6.6808 |

## Repeated Leave-One-Cell-Out Transfer

| target | training_protocol | fewshot_k | runs | median_r2 | min_r2 | median_mae | median_mape_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| delay_avg_ns | source_plus_target_support | 0.0000 | 80.0000 | 0.7542 | 0.4659 | 0.0829 | 25.8995 |
| delay_avg_ns | source_plus_target_support | 20.0000 | 80.0000 | 0.8687 | 0.7148 | 0.0490 | 14.5851 |
| delay_avg_ns | source_plus_target_support | 40.0000 | 80.0000 | 0.8881 | 0.6528 | 0.0460 | 13.7333 |
| delay_avg_ns | target_support_only | 20.0000 | 80.0000 | 0.2665 | -1.3275 | 0.1174 | 44.5490 |
| delay_avg_ns | target_support_only | 40.0000 | 80.0000 | 0.5844 | -1.2427 | 0.0858 | 28.2513 |
| power_avg_uW | source_plus_target_support | 0.0000 | 80.0000 | 0.8901 | 0.4332 | 0.7125 | 16.0052 |
| power_avg_uW | source_plus_target_support | 20.0000 | 80.0000 | 0.9745 | 0.8287 | 0.3540 | 7.8387 |
| power_avg_uW | source_plus_target_support | 40.0000 | 80.0000 | 0.9783 | 0.8791 | 0.3319 | 7.4970 |
| power_avg_uW | target_support_only | 20.0000 | 80.0000 | 0.7922 | 0.4055 | 0.9985 | 21.7634 |
| power_avg_uW | target_support_only | 40.0000 | 80.0000 | 0.9055 | 0.7034 | 0.6982 | 15.5876 |

## Candidate-Ranking Enrichment

| selection | runs | median_top10_hits | median_top20_hits | median_actual_rank | median_actual_score | median_spearman | empirical_p_top10_ge_surrogate | empirical_p_top20_ge_surrogate | empirical_p_rank_le_surrogate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| random_selection | 10000.0000 | 1.0000 | 2.0000 | 48.5000 | 0.2923 | 0.9817 |  |  |  |
| surrogate_top_score | 20.0000 | 9.0000 | 12.0000 | 6.5000 | 0.0612 | 0.9817 | 0.0 | 0.0 | 0.0 |

## Output Files

- `v3_model_zoo_repeated.csv` and summary
- `v3_feature_ablation.csv` and summary
- `v3_learning_curve.csv` and summary
- `v3_corner_holdout.csv` and summary
- `v3_transfer_robustness.csv` and summary
- `v3_candidate_ranking_robustness.csv` and summary
