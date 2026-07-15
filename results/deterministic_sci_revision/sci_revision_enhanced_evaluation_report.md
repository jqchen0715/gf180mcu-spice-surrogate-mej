# SCI Revision Enhanced Evaluation

## Dataset

- Primary SPICE rows: 320.
- Validation SPICE rows: 480.
- Cells: INV, NAND2, NOR2, XOR2.
- Modern optional baselines included: XGBoost=True, LightGBM=True, CatBoost=True.

## Stronger Tabular Baselines and Cost

| target | model | runs | median_r2 | q25_r2 | q75_r2 | median_mae | median_p95_abs_err | median_fit_seconds | median_predict_us_per_row |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| delay_avg_ns | CatBoost | 20 | 0.9193 | 0.8791 | 0.9294 | 0.03366 | 0.09489 | 0.1039 | 57.72 |
| delay_avg_ns | GaussianProcess | 20 | 0.9004 | 0.8803 | 0.9168 | 0.03917 | 0.1161 | 0.1242 | 51.4 |
| delay_avg_ns | XGBoost | 20 | 0.8888 | 0.8726 | 0.9051 | 0.04101 | 0.1318 | 0.07524 | 53.98 |
| delay_avg_ns | GradientBoosting | 20 | 0.8803 | 0.8659 | 0.9082 | 0.04617 | 0.15 | 0.0983 | 47.21 |
| delay_avg_ns | ExtraTrees | 20 | 0.869 | 0.8158 | 0.888 | 0.04986 | 0.1366 | 0.1839 | 685 |
| delay_avg_ns | LightGBM | 20 | 0.8596 | 0.8425 | 0.8679 | 0.04752 | 0.1486 | 0.03465 | 63.91 |
| power_avg_uW | GaussianProcess | 20 | 0.9992 | 0.9992 | 0.9994 | 0.05602 | 0.1602 | 0.1146 | 55.15 |
| power_avg_uW | CatBoost | 20 | 0.9888 | 0.9873 | 0.9899 | 0.2411 | 0.6228 | 0.1042 | 54.62 |
| power_avg_uW | XGBoost | 20 | 0.9809 | 0.9753 | 0.9834 | 0.338 | 0.8564 | 0.07454 | 50.76 |
| power_avg_uW | MLP | 20 | 0.9808 | 0.9704 | 0.9866 | 0.3417 | 0.8652 | 0.2262 | 45.95 |
| power_avg_uW | LightGBM | 20 | 0.9788 | 0.9741 | 0.9802 | 0.3408 | 0.9625 | 0.03413 | 62.69 |
| power_avg_uW | HistGradientBoosting | 20 | 0.9784 | 0.9757 | 0.9805 | 0.3532 | 0.9616 | 2.645 | 924.5 |

## Primary-to-Validation Generalization

| target | model | r2 | mae | p95_abs_err | max_abs_err | fit_seconds | predict_us_per_row |
| --- | --- | --- | --- | --- | --- | --- | --- |
| delay_avg_ns | CatBoost | 0.9208 | 0.03211 | 0.1044 | 0.8072 | 0.07288 | 6.174 |
| delay_avg_ns | GaussianProcess | 0.9207 | 0.03772 | 0.1281 | 0.6163 | 0.2661 | 10.39 |
| delay_avg_ns | XGBoost | 0.8961 | 0.03844 | 0.136 | 0.9135 | 0.06677 | 6.889 |
| delay_avg_ns | GradientBoosting | 0.8894 | 0.04198 | 0.1451 | 0.9008 | 0.1186 | 8.266 |
| delay_avg_ns | HistGradientBoosting | 0.8883 | 0.04074 | 0.1387 | 0.8268 | 1.841 | 127.2 |
| delay_avg_ns | LightGBM | 0.8853 | 0.04124 | 0.145 | 0.7988 | 0.02777 | 12.95 |
| power_avg_uW | GaussianProcess | 0.9994 | 0.04493 | 0.1351 | 0.6669 | 0.1204 | 10.05 |
| power_avg_uW | CatBoost | 0.9902 | 0.2107 | 0.6002 | 2.721 | 0.07038 | 6.322 |
| power_avg_uW | MLP | 0.9878 | 0.2665 | 0.6516 | 1.627 | 0.3445 | 5.27 |
| power_avg_uW | SVR_RBF | 0.9823 | 0.2827 | 0.8647 | 2.998 | 0.01733 | 19.85 |
| power_avg_uW | LightGBM | 0.9817 | 0.3039 | 0.83 | 2.934 | 0.02812 | 13.94 |
| power_avg_uW | XGBoost | 0.9811 | 0.3002 | 0.8827 | 2.789 | 0.05602 | 7.417 |

## Statistical Tests

Friedman tests use repeated-split R2 values across all complete model columns. Wilcoxon tests compare the best median-MAE model with each alternative on paired split MAE values with Holm adjustment.

| target | models | friedman_stat | friedman_p | best_avg_rank_model | best_avg_rank |
| --- | --- | --- | --- | --- | --- |
| delay_avg_ns | CatBoost, ExtraTrees, GaussianProcess, GradientBoosting, HistGradientBoosting, LightGBM, MLP, RandomForest, Ridge, SVR_RBF, XGBoost | 153.9 | 5.945e-28 | CatBoost | 2.1 |
| power_avg_uW | CatBoost, ExtraTrees, GaussianProcess, GradientBoosting, HistGradientBoosting, LightGBM, MLP, RandomForest, Ridge, SVR_RBF, XGBoost | 164.6 | 3.571e-30 | GaussianProcess | 1 |

| target | best_median_mae_model | comparison_model | median_mae_best | median_mae_other | wilcoxon_p_raw | wilcoxon_p_holm |
| --- | --- | --- | --- | --- | --- | --- |
| delay_avg_ns | CatBoost | XGBoost | 0.03366 | 0.04101 | 1.907e-06 | 3.815e-06 |
| delay_avg_ns | CatBoost | SVR_RBF | 0.03366 | 0.05328 | 1.907e-06 | 5.722e-06 |
| delay_avg_ns | CatBoost | Ridge | 0.03366 | 0.08361 | 1.907e-06 | 7.629e-06 |
| delay_avg_ns | CatBoost | RandomForest | 0.03366 | 0.06104 | 1.907e-06 | 9.537e-06 |
| delay_avg_ns | CatBoost | MLP | 0.03366 | 0.07632 | 1.907e-06 | 1.144e-05 |
| delay_avg_ns | CatBoost | LightGBM | 0.03366 | 0.04752 | 1.907e-06 | 1.335e-05 |
| power_avg_uW | GaussianProcess | XGBoost | 0.05602 | 0.338 | 1.907e-06 | 1.907e-06 |
| power_avg_uW | GaussianProcess | SVR_RBF | 0.05602 | 0.3496 | 1.907e-06 | 3.815e-06 |
| power_avg_uW | GaussianProcess | Ridge | 0.05602 | 0.448 | 1.907e-06 | 5.722e-06 |
| power_avg_uW | GaussianProcess | RandomForest | 0.05602 | 0.6654 | 1.907e-06 | 7.629e-06 |
| power_avg_uW | GaussianProcess | MLP | 0.05602 | 0.3417 | 1.907e-06 | 9.537e-06 |
| power_avg_uW | GaussianProcess | LightGBM | 0.05602 | 0.3408 | 1.907e-06 | 1.144e-05 |

## Ranking Metrics

| experiment | median_spearman | median_kendall_tau | median_precision_at_k_top10 | median_recall_at_k_top10 | median_precision_at_k_top20 | median_recall_at_k_top20 | median_ndcg_at_k | median_median_actual_rank_selected |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v2_repeated_holdout | 0.9785 | 0.8814 | 0.5385 | 1 | 0.9231 | 0.9231 | 0.9954 | 7 |
| v2_train_v3_validation | 0.9876 | 0.906 | 0.5 | 1 | 0.9479 | 0.9479 | 0.9985 | 48.5 |

## Conformal Prediction Intervals

| experiment | target | runs | median_empirical_coverage | q25_empirical_coverage | q75_empirical_coverage | median_interval_width | median_abs_err | median_p95_abs_err |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v2_calibrated_v3_external | delay_avg_ns | 1 | 0.9521 | 0.9521 | 0.9521 | 0.3316 | 0.02648 | 0.1589 |
| v2_calibrated_v3_external | power_avg_uW | 1 | 0.9292 | 0.9292 | 0.9292 | 2.19 | 0.2913 | 1.275 |
| v2_split_conformal | delay_avg_ns | 20 | 0.9375 | 0.9062 | 0.9688 | 0.3042 | 0.02948 | 0.1652 |
| v2_split_conformal | power_avg_uW | 20 | 0.9375 | 0.9023 | 0.957 | 2.279 | 0.3348 | 1.225 |

## Permutation Feature Importance

| target | model | feature | importance_mean_delta_r2 | importance_std_delta_r2 |
| --- | --- | --- | --- | --- |
| delay_avg_ns | GradientBoosting | Wn_um | 0.6948 | 0.1216 |
| delay_avg_ns | GradientBoosting | Cload_fF | 0.515 | 0.1716 |
| delay_avg_ns | GradientBoosting | corner | 0.132 | 0.05773 |
| delay_avg_ns | GradientBoosting | cell_type | 0.02863 | 0.01833 |
| delay_avg_ns | GradientBoosting | Vdd | 0.01575 | 0.004203 |
| delay_avg_ns | GradientBoosting | slew_ps | 0.01212 | 0.00253 |
| delay_avg_ns | GradientBoosting | input_arc | 0.009853 | 0.0188 |
| delay_avg_ns | GradientBoosting | Temp | 0.000823 | 0.004482 |
| power_avg_uW | GradientBoosting | Cload_fF | 1.333 | 0.2378 |
| power_avg_uW | GradientBoosting | Wn_um | 0.1187 | 0.02605 |
| power_avg_uW | GradientBoosting | Vdd | 0.1056 | 0.01772 |
| power_avg_uW | GradientBoosting | cell_type | 0.06199 | 0.01354 |
| power_avg_uW | GradientBoosting | input_arc | 0.0268 | 0.007482 |
| power_avg_uW | GradientBoosting | Wp_Wn_ratio | 0.005615 | 0.002057 |
| power_avg_uW | GradientBoosting | L_um | 0 | 0 |
| power_avg_uW | GradientBoosting | Temp | -6.169e-05 | 0.0003095 |

## Parsed SPICE Runtime

| dataset | rows | median_elapsed_s | p90_elapsed_s | total_elapsed_s | group | cell_type |
| --- | --- | --- | --- | --- | --- | --- |
| v3 | 800 | 0.51 | 0.859 | 3123 | dataset |  |
| v3 | 200 | 0.329 | nan | 64.57 | dataset_cell | INV |
| v3 | 200 | 0.481 | nan | 996 | dataset_cell | NAND2 |
| v3 | 200 | 0.527 | nan | 1008 | dataset_cell | NOR2 |
| v3 | 200 | 0.8375 | nan | 1055 | dataset_cell | XOR2 |

## Boundary Note

The enhanced evaluation strengthens tabular surrogate evidence. It does not establish graph-based, cross-PDK, layout-extracted, or online simulator-in-the-loop active learning claims.
