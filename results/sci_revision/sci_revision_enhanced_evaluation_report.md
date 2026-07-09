# SCI Revision Enhanced Evaluation

## Dataset

- Primary SPICE rows: 320.
- Validation SPICE rows: 480.
- Cells: INV, NAND2, NOR2, XOR2.
- Modern optional baselines included: XGBoost=True, LightGBM=True, CatBoost=True.

## Stronger Tabular Baselines and Cost

| target | model | runs | median_r2 | q25_r2 | q75_r2 | median_mae | median_p95_abs_err | median_fit_seconds | median_predict_us_per_row |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| delay_avg_ns | CatBoost | 20 | 0.9163 | 0.8755 | 0.9263 | 0.03474 | 0.09204 | 0.051 | 24.13 |
| delay_avg_ns | GaussianProcess | 20 | 0.8966 | 0.8772 | 0.9155 | 0.03995 | 0.118 | 0.0472 | 22.06 |
| delay_avg_ns | XGBoost | 20 | 0.8846 | 0.873 | 0.9055 | 0.04191 | 0.1228 | 0.02901 | 22.11 |
| delay_avg_ns | GradientBoosting | 20 | 0.8807 | 0.8588 | 0.9 | 0.0475 | 0.1639 | 0.03672 | 19.46 |
| delay_avg_ns | ExtraTrees | 20 | 0.8644 | 0.8171 | 0.8839 | 0.04959 | 0.1319 | 0.06494 | 231.8 |
| delay_avg_ns | LightGBM | 20 | 0.855 | 0.8379 | 0.8727 | 0.0463 | 0.1502 | 0.0134 | 24.73 |
| power_avg_uW | GaussianProcess | 20 | 0.9992 | 0.9992 | 0.9994 | 0.05593 | 0.1609 | 0.04429 | 22.54 |
| power_avg_uW | CatBoost | 20 | 0.989 | 0.9878 | 0.9908 | 0.2393 | 0.6198 | 0.05022 | 23.61 |
| power_avg_uW | MLP | 20 | 0.9819 | 0.9704 | 0.9866 | 0.3323 | 0.8521 | 0.09292 | 20.38 |
| power_avg_uW | XGBoost | 20 | 0.9811 | 0.9761 | 0.9827 | 0.3365 | 0.852 | 0.02905 | 22.57 |
| power_avg_uW | HistGradientBoosting | 20 | 0.9793 | 0.975 | 0.9802 | 0.3552 | 0.9225 | 0.2641 | 93.56 |
| power_avg_uW | LightGBM | 20 | 0.979 | 0.9733 | 0.981 | 0.3318 | 0.9571 | 0.01328 | 25.24 |

## Primary-to-Validation Generalization

| target | model | r2 | mae | p95_abs_err | max_abs_err | fit_seconds | predict_us_per_row |
| --- | --- | --- | --- | --- | --- | --- | --- |
| delay_avg_ns | CatBoost | 0.9187 | 0.03173 | 0.1004 | 0.8357 | 0.05298 | 4.192 |
| delay_avg_ns | GaussianProcess | 0.9176 | 0.03795 | 0.1299 | 0.6254 | 0.1518 | 5.986 |
| delay_avg_ns | XGBoost | 0.8963 | 0.03836 | 0.1282 | 0.9005 | 0.02987 | 3.845 |
| delay_avg_ns | GradientBoosting | 0.8907 | 0.04191 | 0.1534 | 0.9081 | 0.04456 | 3.998 |
| delay_avg_ns | HistGradientBoosting | 0.8884 | 0.04021 | 0.1354 | 0.8174 | 0.3429 | 17.12 |
| delay_avg_ns | LightGBM | 0.8854 | 0.03976 | 0.1365 | 0.798 | 0.01612 | 7.755 |
| power_avg_uW | GaussianProcess | 0.9994 | 0.04527 | 0.1385 | 0.6606 | 0.06685 | 5.977 |
| power_avg_uW | CatBoost | 0.9902 | 0.2105 | 0.5885 | 2.689 | 0.04758 | 3.754 |
| power_avg_uW | MLP | 0.9878 | 0.266 | 0.6729 | 1.643 | 0.1586 | 3.161 |
| power_avg_uW | SVR_RBF | 0.9824 | 0.2829 | 0.8666 | 2.992 | 0.007913 | 9.466 |
| power_avg_uW | LightGBM | 0.9817 | 0.3046 | 0.8784 | 2.891 | 0.0153 | 7.41 |
| power_avg_uW | XGBoost | 0.9808 | 0.3065 | 0.8726 | 2.725 | 0.02926 | 4.031 |

## Statistical Tests

Friedman tests use repeated-split R2 values across all complete model columns. Wilcoxon tests compare the best median-MAE model with each alternative on paired split MAE values with Holm adjustment.

| target | models | friedman_stat | friedman_p | best_avg_rank_model | best_avg_rank |
| --- | --- | --- | --- | --- | --- |
| delay_avg_ns | CatBoost, ExtraTrees, GaussianProcess, GradientBoosting, HistGradientBoosting, LightGBM, MLP, RandomForest, Ridge, SVR_RBF, XGBoost | 153.2 | 8.179e-28 | CatBoost | 1.9 |
| power_avg_uW | CatBoost, ExtraTrees, GaussianProcess, GradientBoosting, HistGradientBoosting, LightGBM, MLP, RandomForest, Ridge, SVR_RBF, XGBoost | 166.5 | 1.496e-30 | GaussianProcess | 1 |

| target | best_median_mae_model | comparison_model | median_mae_best | median_mae_other | wilcoxon_p_raw | wilcoxon_p_holm |
| --- | --- | --- | --- | --- | --- | --- |
| delay_avg_ns | CatBoost | XGBoost | 0.03474 | 0.04191 | 1.907e-06 | 3.815e-06 |
| delay_avg_ns | CatBoost | SVR_RBF | 0.03474 | 0.05406 | 1.907e-06 | 5.722e-06 |
| delay_avg_ns | CatBoost | Ridge | 0.03474 | 0.08285 | 1.907e-06 | 7.629e-06 |
| delay_avg_ns | CatBoost | RandomForest | 0.03474 | 0.06087 | 1.907e-06 | 9.537e-06 |
| delay_avg_ns | CatBoost | MLP | 0.03474 | 0.0741 | 1.907e-06 | 1.144e-05 |
| delay_avg_ns | CatBoost | LightGBM | 0.03474 | 0.0463 | 1.907e-06 | 1.335e-05 |
| power_avg_uW | GaussianProcess | XGBoost | 0.05593 | 0.3365 | 1.907e-06 | 1.907e-06 |
| power_avg_uW | GaussianProcess | SVR_RBF | 0.05593 | 0.3503 | 1.907e-06 | 3.815e-06 |
| power_avg_uW | GaussianProcess | Ridge | 0.05593 | 0.4481 | 1.907e-06 | 5.722e-06 |
| power_avg_uW | GaussianProcess | RandomForest | 0.05593 | 0.6656 | 1.907e-06 | 7.629e-06 |
| power_avg_uW | GaussianProcess | MLP | 0.05593 | 0.3323 | 1.907e-06 | 9.537e-06 |
| power_avg_uW | GaussianProcess | LightGBM | 0.05593 | 0.3318 | 1.907e-06 | 1.144e-05 |

## Ranking Metrics

| experiment | median_spearman | median_kendall_tau | median_precision_at_k_top10 | median_recall_at_k_top10 | median_precision_at_k_top20 | median_recall_at_k_top20 | median_ndcg_at_k | median_median_actual_rank_selected |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v2_repeated_holdout | 0.9774 | 0.8874 | 0.5385 | 1 | 0.8846 | 0.8846 | 0.9956 | 7 |
| v2_train_v3_validation | 0.987 | 0.9031 | 0.5 | 1 | 0.9479 | 0.9479 | 0.9984 | 48.5 |

## Conformal Prediction Intervals

| experiment | target | runs | median_empirical_coverage | q25_empirical_coverage | q75_empirical_coverage | median_interval_width | median_abs_err | median_p95_abs_err |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v2_calibrated_v3_external | delay_avg_ns | 1 | 0.9437 | 0.9437 | 0.9437 | 0.3202 | 0.02527 | 0.1658 |
| v2_calibrated_v3_external | power_avg_uW | 1 | 0.9396 | 0.9396 | 0.9396 | 2.158 | 0.2928 | 1.222 |
| v2_split_conformal | delay_avg_ns | 20 | 0.9453 | 0.9023 | 0.957 | 0.3381 | 0.03003 | 0.1731 |
| v2_split_conformal | power_avg_uW | 20 | 0.9375 | 0.9062 | 0.9688 | 2.416 | 0.3342 | 1.215 |

## Permutation Feature Importance

| target | model | feature | importance_mean_delta_r2 | importance_std_delta_r2 |
| --- | --- | --- | --- | --- |
| delay_avg_ns | GradientBoosting | Wn_um | 0.7067 | 0.1199 |
| delay_avg_ns | GradientBoosting | Cload_fF | 0.5274 | 0.1693 |
| delay_avg_ns | GradientBoosting | corner | 0.1488 | 0.06295 |
| delay_avg_ns | GradientBoosting | cell_type | 0.02592 | 0.01691 |
| delay_avg_ns | GradientBoosting | slew_ps | 0.01503 | 0.003487 |
| delay_avg_ns | GradientBoosting | Vdd | 0.01385 | 0.005821 |
| delay_avg_ns | GradientBoosting | input_arc | 0.01104 | 0.01555 |
| delay_avg_ns | GradientBoosting | Wp_Wn_ratio | 0.0007525 | 0.008121 |
| power_avg_uW | GradientBoosting | Cload_fF | 1.337 | 0.2346 |
| power_avg_uW | GradientBoosting | Wn_um | 0.1203 | 0.02521 |
| power_avg_uW | GradientBoosting | Vdd | 0.1056 | 0.01653 |
| power_avg_uW | GradientBoosting | input_arc | 0.05355 | 0.01132 |
| power_avg_uW | GradientBoosting | cell_type | 0.03356 | 0.009158 |
| power_avg_uW | GradientBoosting | Wp_Wn_ratio | 0.006368 | 0.002274 |
| power_avg_uW | GradientBoosting | slew_ps | 0.0002703 | 0.0006629 |
| power_avg_uW | GradientBoosting | Temp | 3.985e-05 | 0.0003626 |

## Parsed SPICE Runtime

| dataset | rows | median_elapsed_s | p90_elapsed_s | total_elapsed_s | group | cell_type |
| --- | --- | --- | --- | --- | --- | --- |
| v2 | 320 | 0.602 | 1.015 | 215 | dataset |  |
| v3 | 480 | 0.7445 | 1.34 | 401.3 | dataset |  |
| v2 | 80 | 0.432 | nan | 35.43 | dataset_cell | INV |
| v2 | 80 | 0.608 | nan | 49.25 | dataset_cell | NAND2 |
| v2 | 80 | 0.5955 | nan | 48.1 | dataset_cell | NOR2 |
| v2 | 80 | 1.007 | nan | 82.26 | dataset_cell | XOR2 |
| v3 | 120 | 0.426 | nan | 56.07 | dataset_cell | INV |
| v3 | 120 | 0.679 | nan | 88.72 | dataset_cell | NAND2 |
| v3 | 120 | 0.7785 | nan | 93.75 | dataset_cell | NOR2 |
| v3 | 120 | 1.305 | nan | 162.8 | dataset_cell | XOR2 |

## Boundary Note

The enhanced evaluation strengthens tabular surrogate evidence. It does not establish graph-based, cross-PDK, layout-extracted, or online simulator-in-the-loop active learning claims.
