# V2-Only Acquisition-Weight Tuning

The independent V3 validation dataset was not used in this tuning step.
The primary selection criterion was the median area under the worst-cell delay-R2 learning curve.

| uncertainty_weight | diversity_weight | runs | median_worst_cell_delay_r2_aulc | q25_worst_cell_delay_r2_aulc | q75_worst_cell_delay_r2_aulc | median_overall_delay_r2_aulc | median_top20_recall_aulc |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.0000 | 1.0000 | 30 | 0.3342 | -0.1301 | 0.4921 | 0.7005 | 0.8889 |
| 0.2500 | 0.7500 | 30 | -0.0808 | -0.6256 | 0.3843 | 0.6109 | 0.8889 |
| 0.5000 | 0.5000 | 30 | -0.5478 | -1.4961 | 0.2845 | 0.5473 | 0.8889 |
| 0.7500 | 0.2500 | 30 | -0.7998 | -2.0407 | 0.2338 | 0.4837 | 0.8796 |
| 1.0000 | 0.0000 | 30 | -0.8802 | -1.9297 | 0.2222 | 0.4918 | 0.8889 |

Selected uncertainty weight: 0.00
Selected diversity weight: 1.00
