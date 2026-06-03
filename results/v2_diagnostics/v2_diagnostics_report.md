# Primary-Dataset Diagnostics and SPICE-Verified Case Study

## Held-Out Metrics

| target | model | test_rows | r2 | mae | rmse | mape_pct |
| --- | --- | --- | --- | --- | --- | --- |
| delay_avg_ns | GradientBoosting | 64.0000 | 0.8708 | 0.0483 | 0.0950 | 17.9177 |
| power_avg_uW | GradientBoosting | 64.0000 | 0.9696 | 0.4372 | 0.5776 | 8.6970 |

## Error by Cell Type

| cell_type | rows | median_delay_mape | median_power_mape | max_delay_abs_err_ns | max_power_abs_err_uW |
| --- | --- | --- | --- | --- | --- |
| INV | 16.0000 | 23.5767 | 7.6120 | 0.1677 | 0.8738 |
| NAND2 | 16.0000 | 13.0104 | 5.0249 | 0.5687 | 1.2543 |
| NOR2 | 16.0000 | 10.1319 | 5.3609 | 0.2184 | 1.0604 |
| XOR2 | 16.0000 | 4.9031 | 11.3425 | 0.2562 | 1.7119 |

## Pareto Case Study Summary

| predicted_front_size | actual_front_size | selected_candidates | selected_actual_pareto_hits | selected_actual_pareto_hit_rate | selected_actual_top10pct_hits | selected_actual_top20pct_hits | selected_median_actual_composite_rank | front_overlap_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4.0000 | 1.0000 | 12.0000 | 1.0000 | 0.0833 | 7.0000 | 11.0000 | 6.5000 | 1.0000 |

## Surrogate-Selected Candidates

| sample_id | cell_type | corner | delay_avg_ns | power_avg_uW | pred_delay_avg_ns | pred_power_avg_uW | pred_composite_score | actual_composite_score | actual_composite_rank | actual_pareto_member | actual_top10pct_member | actual_top20pct_member |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 60.0000 | INV | typical | 0.0648 | 0.6537 | 0.1327 | 0.6214 | 0.0302 | 0.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| 139.0000 | NAND2 | ff | 0.1388 | 1.6764 | 0.1225 | 1.2732 | 0.0502 | 0.0603 | 4.0000 | 0.0000 | 1.0000 | 1.0000 |
| 69.0000 | INV | typical | 0.0773 | 2.1601 | 0.0805 | 1.9281 | 0.0548 | 0.0586 | 2.0000 | 0.0000 | 1.0000 | 1.0000 |
| 63.0000 | INV | typical | 0.0903 | 2.3592 | 0.0711 | 2.5651 | 0.0747 | 0.0699 | 6.0000 | 0.0000 | 1.0000 | 1.0000 |
| 112.0000 | NAND2 | ff | 0.1470 | 1.9920 | 0.1391 | 1.8986 | 0.0824 | 0.0743 | 8.0000 | 0.0000 | 0.0000 | 1.0000 |
| 210.0000 | NOR2 | ff | 0.0967 | 2.6210 | 0.1035 | 2.5953 | 0.0917 | 0.0814 | 9.0000 | 0.0000 | 0.0000 | 1.0000 |
| 20.0000 | INV | ff | 0.1341 | 2.0949 | 0.1333 | 2.3100 | 0.0954 | 0.0740 | 7.0000 | 0.0000 | 1.0000 | 1.0000 |
| 160.0000 | NOR2 | typical | 0.1470 | 1.5952 | 0.1860 | 1.6433 | 0.0956 | 0.0599 | 3.0000 | 0.0000 | 1.0000 | 1.0000 |
| 196.0000 | NOR2 | typical | 0.2211 | 1.7725 | 0.1739 | 1.9170 | 0.1002 | 0.0896 | 10.0000 | 0.0000 | 0.0000 | 1.0000 |
| 23.0000 | INV | ff | 0.0893 | 2.2418 | 0.1425 | 2.6079 | 0.1114 | 0.0653 | 5.0000 | 0.0000 | 1.0000 | 1.0000 |
| 52.0000 | INV | ss | 0.1659 | 2.4682 | 0.1734 | 2.3631 | 0.1171 | 0.0975 | 11.0000 | 0.0000 | 0.0000 | 1.0000 |
| 187.0000 | NOR2 | typical | 0.0913 | 4.0776 | 0.0967 | 3.4602 | 0.1217 | 0.1325 | 16.0000 | 0.0000 | 0.0000 | 0.0000 |

## Output Files

- `v2_predictions_holdout.csv`
- `v2_pareto_selected_candidates.csv`
- `v2_predicted_vs_spice.png` / `.pdf`
- `v2_error_by_cell.png` / `.pdf`
- `v2_spice_verified_pareto_case.png` / `.pdf`
