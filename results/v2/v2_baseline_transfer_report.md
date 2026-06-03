# V2 Baseline and Transfer Report

## Dataset

- Rows used: 320
- Cells: INV, NAND2, NOR2, XOR2
- Fidelity: SPICE_GF180MCU
- Status values: ok

## Best Random-Split Models

| target | model | r2 | mae | rmse | mape_pct |
| --- | --- | --- | --- | --- | --- |
| delay_avg_ns | GradientBoosting | 0.8708 | 0.0483 | 0.0950 | 17.9177 |
| power_avg_uW | GradientBoosting | 0.9696 | 0.4372 | 0.5776 | 8.6970 |

## Transfer Protocol

Leave-one-cell-out transfer is evaluated with k-shot support samples from the target cell.
Rows with k=0 are zero-shot transfer results.
From-scratch few-shot baselines are trained only on the k target-cell support samples and are reported for k>0.

## Transfer Summary

| target | fewshot_k | median_r2 | min_r2 | median_mae | median_mape_pct |
| --- | --- | --- | --- | --- | --- |
| delay_avg_ns | 0.0000 | 0.7365 | 0.4336 | 0.0841 | 27.7045 |
| delay_avg_ns | 5.0000 | 0.8359 | 0.5748 | 0.0614 | 19.9788 |
| delay_avg_ns | 10.0000 | 0.8222 | 0.6647 | 0.0682 | 16.9438 |
| delay_avg_ns | 20.0000 | 0.8467 | 0.7567 | 0.0470 | 18.6704 |
| delay_avg_ns | 40.0000 | 0.8807 | 0.8481 | 0.0479 | 17.5515 |
| power_avg_uW | 0.0000 | 0.8966 | 0.5819 | 0.6209 | 14.3443 |
| power_avg_uW | 5.0000 | 0.9570 | 0.7825 | 0.3998 | 10.8817 |
| power_avg_uW | 10.0000 | 0.9371 | 0.8054 | 0.5258 | 11.9195 |
| power_avg_uW | 20.0000 | 0.9796 | 0.9540 | 0.3494 | 7.7998 |
| power_avg_uW | 40.0000 | 0.9807 | 0.9737 | 0.3350 | 7.0887 |

## From-Scratch Few-Shot Summary

| target | fewshot_k | median_r2 | min_r2 | median_mae | median_mape_pct |
| --- | --- | --- | --- | --- | --- |
| delay_avg_ns | 5.0000 | 0.0409 | -0.0765 | 0.1663 | 66.0615 |
| delay_avg_ns | 10.0000 | 0.1506 | 0.1108 | 0.1295 | 40.2941 |
| delay_avg_ns | 20.0000 | 0.2530 | -0.4293 | 0.1236 | 52.3012 |
| delay_avg_ns | 40.0000 | 0.5483 | 0.4663 | 0.0852 | 30.2554 |
| power_avg_uW | 5.0000 | 0.2148 | -0.1864 | 2.3421 | 55.7811 |
| power_avg_uW | 10.0000 | 0.7015 | 0.5746 | 1.3866 | 30.7292 |
| power_avg_uW | 20.0000 | 0.8188 | 0.7737 | 0.9831 | 23.0619 |
| power_avg_uW | 40.0000 | 0.8992 | 0.8939 | 0.7692 | 16.5703 |

## Transfer vs From-Scratch Gain

| target | fewshot_k | median_r2_transfer | median_r2_scratch | median_r2_gain | median_mae_transfer | median_mae_scratch |
| --- | --- | --- | --- | --- | --- | --- |
| delay_avg_ns | 5.0000 | 0.8359 | 0.0409 | 0.7950 | 0.0614 | 0.1663 |
| delay_avg_ns | 10.0000 | 0.8222 | 0.1506 | 0.6716 | 0.0682 | 0.1295 |
| delay_avg_ns | 20.0000 | 0.8467 | 0.2530 | 0.5937 | 0.0470 | 0.1236 |
| delay_avg_ns | 40.0000 | 0.8807 | 0.5483 | 0.3324 | 0.0479 | 0.0852 |
| power_avg_uW | 5.0000 | 0.9570 | 0.2148 | 0.7422 | 0.3998 | 2.3421 |
| power_avg_uW | 10.0000 | 0.9371 | 0.7015 | 0.2356 | 0.5258 | 1.3866 |
| power_avg_uW | 20.0000 | 0.9796 | 0.8188 | 0.1608 | 0.3494 | 0.9831 |
| power_avg_uW | 40.0000 | 0.9807 | 0.8992 | 0.0815 | 0.3350 | 0.7692 |

## Zero-Shot Best Models by Held-Out Cell

| target | heldout_cell | model | r2 | mae | rmse | mape_pct |
| --- | --- | --- | --- | --- | --- | --- |
| delay_avg_ns | INV | MLP | 0.4336 | 0.1051 | 0.1321 | 58.2110 |
| delay_avg_ns | NAND2 | GradientBoosting | 0.8424 | 0.0568 | 0.0890 | 24.3262 |
| delay_avg_ns | NOR2 | GradientBoosting | 0.8036 | 0.0630 | 0.1060 | 15.7333 |
| delay_avg_ns | XOR2 | GradientBoosting | 0.6694 | 0.1133 | 0.1345 | 31.0828 |
| power_avg_uW | INV | MLP | 0.8158 | 0.8982 | 1.1026 | 21.6090 |
| power_avg_uW | NAND2 | GradientBoosting | 0.9773 | 0.3436 | 0.4534 | 6.3593 |
| power_avg_uW | NOR2 | GradientBoosting | 0.9805 | 0.3305 | 0.4162 | 7.0796 |
| power_avg_uW | XOR2 | GradientBoosting | 0.5819 | 1.9381 | 2.2963 | 25.2554 |

## Output Files

- `v2_baseline_transfer_results.csv`
- `v2_dataset_summary.json`
