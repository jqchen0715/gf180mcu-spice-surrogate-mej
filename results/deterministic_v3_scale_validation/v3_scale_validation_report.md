# V3 Scale-Up and Corner-Support Validation

## Dataset

- V2 training rows: 320 publication-eligible GF180MCU/ngspice rows.
- V3 validation rows: 480 publication-eligible GF180MCU/ngspice rows.
- V3 cells: INV, NAND2, NOR2, XOR2.
- V3 corners: ff, ss, typical.

## V2-Trained External Validation on V3

| experiment | target | model | train_rows | test_rows | r2 | mae | rmse | mape_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v2_train_v3_external_validation | delay_avg_ns | GradientBoosting | 320.0000 | 480.0000 | 0.8894 | 0.0420 | 0.0812 | 12.6463 |
| v2_train_v3_external_validation | delay_avg_ns | SVR_RBF | 320.0000 | 480.0000 | 0.8779 | 0.0482 | 0.0854 | 18.5681 |
| v2_train_v3_external_validation | delay_avg_ns | MLP | 320.0000 | 480.0000 | 0.8303 | 0.0676 | 0.1006 | 27.4561 |
| v2_train_v3_external_validation | power_avg_uW | GradientBoosting | 320.0000 | 480.0000 | 0.9744 | 0.3599 | 0.4998 | 6.3683 |
| v2_train_v3_external_validation | power_avg_uW | SVR_RBF | 320.0000 | 480.0000 | 0.9823 | 0.2827 | 0.4152 | 7.3539 |
| v2_train_v3_external_validation | power_avg_uW | MLP | 320.0000 | 480.0000 | 0.9878 | 0.2665 | 0.3454 | 6.1170 |

## V2-Trained Candidate Ranking on V3

| selection | runs | median_top10_hits | median_top20_hits | median_actual_rank | median_actual_score | median_spearman | empirical_p_top10_ge_surrogate | empirical_p_top20_ge_surrogate | empirical_p_rank_le_surrogate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| random_selection | 10000.0000 | 2.0000 | 5.0000 | 241.5000 | 0.2524 | 0.9876 |  |  |  |
| v2_surrogate_top_score | 1.0000 | 24.0000 | 24.0000 | 13.5000 | 0.0423 | 0.9876 | 0.0 | 0.0 | 0.0 |

## Corner-Support Calibration on V3

| target | heldout_corner | support_rows | runs | median_r2 | q25_r2 | q75_r2 | median_mae | median_mape_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| delay_avg_ns | ff | 0.0000 | 20.0000 | 0.2336 | 0.1205 | 0.3104 | 0.1172 | 55.3554 |
| delay_avg_ns | ff | 12.0000 | 20.0000 | 0.6353 | 0.5795 | 0.7275 | 0.0629 | 25.2516 |
| delay_avg_ns | ff | 24.0000 | 20.0000 | 0.7831 | 0.7013 | 0.8007 | 0.0474 | 20.1041 |
| delay_avg_ns | ff | 48.0000 | 20.0000 | 0.8213 | 0.7573 | 0.8545 | 0.0414 | 17.8823 |
| delay_avg_ns | ss | 0.0000 | 20.0000 | 0.5543 | 0.5341 | 0.5679 | 0.1435 | 28.4269 |
| delay_avg_ns | ss | 12.0000 | 20.0000 | 0.7465 | 0.7008 | 0.8283 | 0.0880 | 18.1670 |
| delay_avg_ns | ss | 24.0000 | 20.0000 | 0.7632 | 0.7361 | 0.8214 | 0.0837 | 16.3209 |
| delay_avg_ns | ss | 48.0000 | 20.0000 | 0.8084 | 0.7642 | 0.8381 | 0.0771 | 15.4446 |
| delay_avg_ns | typical | 0.0000 | 20.0000 | 0.8399 | 0.7984 | 0.8617 | 0.0437 | 17.2527 |
| delay_avg_ns | typical | 12.0000 | 20.0000 | 0.8639 | 0.8548 | 0.8765 | 0.0391 | 13.8739 |
| delay_avg_ns | typical | 24.0000 | 20.0000 | 0.8866 | 0.8632 | 0.9039 | 0.0374 | 13.3739 |
| delay_avg_ns | typical | 48.0000 | 20.0000 | 0.8934 | 0.8745 | 0.9089 | 0.0363 | 12.3119 |
| power_avg_uW | ff | 0.0000 | 20.0000 | 0.9634 | 0.9633 | 0.9635 | 0.4297 | 9.6183 |
| power_avg_uW | ff | 12.0000 | 20.0000 | 0.9658 | 0.9646 | 0.9688 | 0.4118 | 8.9857 |
| power_avg_uW | ff | 24.0000 | 20.0000 | 0.9670 | 0.9638 | 0.9730 | 0.4118 | 8.6183 |
| power_avg_uW | ff | 48.0000 | 20.0000 | 0.9709 | 0.9672 | 0.9756 | 0.3864 | 8.3105 |
| power_avg_uW | ss | 0.0000 | 20.0000 | 0.9752 | 0.9752 | 0.9753 | 0.3521 | 5.9611 |
| power_avg_uW | ss | 12.0000 | 20.0000 | 0.9744 | 0.9735 | 0.9753 | 0.3449 | 5.6342 |
| power_avg_uW | ss | 24.0000 | 20.0000 | 0.9734 | 0.9711 | 0.9756 | 0.3485 | 5.7467 |
| power_avg_uW | ss | 48.0000 | 20.0000 | 0.9742 | 0.9727 | 0.9759 | 0.3429 | 5.4702 |
| power_avg_uW | typical | 0.0000 | 20.0000 | 0.9769 | 0.9769 | 0.9770 | 0.3541 | 7.0435 |
| power_avg_uW | typical | 12.0000 | 20.0000 | 0.9738 | 0.9724 | 0.9752 | 0.3532 | 6.8477 |
| power_avg_uW | typical | 24.0000 | 20.0000 | 0.9745 | 0.9724 | 0.9766 | 0.3499 | 6.9803 |
| power_avg_uW | typical | 48.0000 | 20.0000 | 0.9754 | 0.9732 | 0.9772 | 0.3506 | 6.8943 |
