# Primary-Dataset Active-Learning Sample-Efficiency Report

## Dataset and Protocol

- Rows used: 320 publication-eligible GF180MCU/ngspice rows.
- Evaluation protocol: stratified train/test split, then pool-based acquisition from the training pool.
- Initial labeled set: 5 rows per cell, 20 rows total.
- Batch size: 20 rows.
- Model: RandomForestRegressor; uncertainty is the standard deviation across trees.
- Strategies: random sampling, uncertainty-guided acquisition, and a hybrid strategy that uses random sampling until 80 labels and uncertainty afterward.

## Budget Comparison

| target | labeled_rows | median_mae_hybrid_random_then_uncertainty | median_mae_random | median_mae_uncertainty | median_r2_hybrid_random_then_uncertainty | median_r2_random | median_r2_uncertainty | median_r2_gain_uncertainty | median_mae_reduction_uncertainty | median_r2_gain_hybrid_random_then_uncertainty | median_mae_reduction_hybrid_random_then_uncertainty |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| delay_avg_ns | 20.0000 | 0.1060 | 0.1060 | 0.1060 | 0.3618 | 0.3618 | 0.3618 | 0.0000 | 0.0000 | -0.0000 | -0.0000 |
| delay_avg_ns | 40.0000 | 0.0999 | 0.0999 | 0.0916 | 0.5292 | 0.5292 | 0.4890 | -0.0402 | 0.0083 | 0.0000 | 0.0000 |
| delay_avg_ns | 80.0000 | 0.0794 | 0.0794 | 0.0744 | 0.6586 | 0.6586 | 0.6706 | 0.0120 | 0.0050 | -0.0000 | 0.0000 |
| delay_avg_ns | 120.0000 | 0.0679 | 0.0736 | 0.0739 | 0.7355 | 0.6994 | 0.7593 | 0.0599 | -0.0003 | 0.0361 | 0.0057 |
| delay_avg_ns | 160.0000 | 0.0636 | 0.0624 | 0.0698 | 0.7764 | 0.7257 | 0.7602 | 0.0345 | -0.0074 | 0.0507 | -0.0012 |
| delay_avg_ns | 200.0000 | 0.0606 | 0.0631 | 0.0645 | 0.7826 | 0.7594 | 0.7705 | 0.0111 | -0.0014 | 0.0232 | 0.0025 |
| power_avg_uW | 20.0000 | 1.4202 | 1.4202 | 1.4202 | 0.6934 | 0.6934 | 0.6934 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| power_avg_uW | 40.0000 | 1.1559 | 1.1559 | 1.2515 | 0.8189 | 0.8189 | 0.7270 | -0.0919 | -0.0956 | 0.0000 | 0.0000 |
| power_avg_uW | 80.0000 | 0.9519 | 0.9519 | 1.1072 | 0.8372 | 0.8372 | 0.8190 | -0.0182 | -0.1553 | 0.0000 | -0.0000 |
| power_avg_uW | 120.0000 | 0.9145 | 0.8392 | 0.8819 | 0.8470 | 0.8728 | 0.8795 | 0.0067 | -0.0427 | -0.0258 | -0.0753 |
| power_avg_uW | 160.0000 | 0.7749 | 0.7759 | 0.8076 | 0.8941 | 0.8976 | 0.9024 | 0.0048 | -0.0317 | -0.0036 | 0.0011 |
| power_avg_uW | 200.0000 | 0.7404 | 0.7517 | 0.7323 | 0.9151 | 0.9077 | 0.9218 | 0.0140 | 0.0193 | 0.0074 | 0.0112 |

## Output Files

- `v2_active_learning_results.csv`
- `v2_active_learning_summary.csv`
- `v2_active_learning_budget_comparison.csv`
- `v2_active_learning_curves.png`
- `v2_active_learning_curves.pdf`
