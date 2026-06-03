# V3 Scale-Up and Corner-Support Validation

## Dataset

- V2 training rows: 320 publication-eligible GF180MCU/ngspice rows.
- V3 validation rows: 480 publication-eligible GF180MCU/ngspice rows.
- V3 cells: INV, NAND2, NOR2, XOR2.
- V3 corners: ff, ss, typical.

## V2-Trained External Validation on V3

| experiment | target | model | train_rows | test_rows | r2 | mae | rmse | mape_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v2_train_v3_external_validation | delay_avg_ns | GradientBoosting | 320.0000 | 480.0000 | 0.8907 | 0.0419 | 0.0809 | 12.2882 |
| v2_train_v3_external_validation | delay_avg_ns | SVR_RBF | 320.0000 | 480.0000 | 0.8758 | 0.0481 | 0.0862 | 18.5132 |
| v2_train_v3_external_validation | delay_avg_ns | MLP | 320.0000 | 480.0000 | 0.8272 | 0.0681 | 0.1017 | 27.6891 |
| v2_train_v3_external_validation | power_avg_uW | GradientBoosting | 320.0000 | 480.0000 | 0.9749 | 0.3591 | 0.4944 | 6.4543 |
| v2_train_v3_external_validation | power_avg_uW | SVR_RBF | 320.0000 | 480.0000 | 0.9824 | 0.2829 | 0.4148 | 7.3566 |
| v2_train_v3_external_validation | power_avg_uW | MLP | 320.0000 | 480.0000 | 0.9878 | 0.2660 | 0.3455 | 6.1142 |

## V2-Trained Candidate Ranking on V3

| selection | runs | median_top10_hits | median_top20_hits | median_actual_rank | median_actual_score | median_spearman | empirical_p_top10_ge_surrogate | empirical_p_top20_ge_surrogate | empirical_p_rank_le_surrogate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| random_selection | 10000.0000 | 2.0000 | 5.0000 | 241.5000 | 0.2522 | 0.9870 |  |  |  |
| v2_surrogate_top_score | 1.0000 | 24.0000 | 24.0000 | 12.5000 | 0.0407 | 0.9870 | 0.0 | 0.0 | 0.0 |

## Corner-Support Calibration on V3

| target | heldout_corner | support_rows | runs | median_r2 | q25_r2 | q75_r2 | median_mae | median_mape_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| delay_avg_ns | ff | 0.0000 | 20.0000 | 0.1645 | 0.0784 | 0.2446 | 0.1178 | 55.6856 |
| delay_avg_ns | ff | 12.0000 | 20.0000 | 0.6373 | 0.5733 | 0.7326 | 0.0607 | 24.9065 |
| delay_avg_ns | ff | 24.0000 | 20.0000 | 0.7641 | 0.7032 | 0.8091 | 0.0488 | 20.3222 |
| delay_avg_ns | ff | 48.0000 | 20.0000 | 0.8167 | 0.7589 | 0.8494 | 0.0421 | 17.6151 |
| delay_avg_ns | ss | 0.0000 | 20.0000 | 0.5418 | 0.5334 | 0.5488 | 0.1450 | 28.8609 |
| delay_avg_ns | ss | 12.0000 | 20.0000 | 0.7478 | 0.7191 | 0.8218 | 0.0864 | 17.0390 |
| delay_avg_ns | ss | 24.0000 | 20.0000 | 0.7591 | 0.7306 | 0.8300 | 0.0831 | 16.2247 |
| delay_avg_ns | ss | 48.0000 | 20.0000 | 0.8068 | 0.7807 | 0.8329 | 0.0794 | 15.3250 |
| delay_avg_ns | typical | 0.0000 | 20.0000 | 0.8333 | 0.8088 | 0.8452 | 0.0477 | 18.9704 |
| delay_avg_ns | typical | 12.0000 | 20.0000 | 0.8633 | 0.8337 | 0.8824 | 0.0402 | 14.8623 |
| delay_avg_ns | typical | 24.0000 | 20.0000 | 0.8920 | 0.8764 | 0.8982 | 0.0368 | 13.3312 |
| delay_avg_ns | typical | 48.0000 | 20.0000 | 0.8936 | 0.8787 | 0.9053 | 0.0361 | 12.7267 |
| power_avg_uW | ff | 0.0000 | 20.0000 | 0.9652 | 0.9651 | 0.9652 | 0.4223 | 9.1820 |
| power_avg_uW | ff | 12.0000 | 20.0000 | 0.9665 | 0.9644 | 0.9676 | 0.4124 | 8.9257 |
| power_avg_uW | ff | 24.0000 | 20.0000 | 0.9657 | 0.9644 | 0.9723 | 0.4083 | 8.7301 |
| power_avg_uW | ff | 48.0000 | 20.0000 | 0.9718 | 0.9685 | 0.9751 | 0.3858 | 8.2800 |
| power_avg_uW | ss | 0.0000 | 20.0000 | 0.9752 | 0.9752 | 0.9753 | 0.3522 | 5.8911 |
| power_avg_uW | ss | 12.0000 | 20.0000 | 0.9744 | 0.9738 | 0.9760 | 0.3464 | 5.6079 |
| power_avg_uW | ss | 24.0000 | 20.0000 | 0.9738 | 0.9726 | 0.9756 | 0.3483 | 5.6967 |
| power_avg_uW | ss | 48.0000 | 20.0000 | 0.9749 | 0.9738 | 0.9766 | 0.3419 | 5.4857 |
| power_avg_uW | typical | 0.0000 | 20.0000 | 0.9768 | 0.9767 | 0.9768 | 0.3478 | 6.9044 |
| power_avg_uW | typical | 12.0000 | 20.0000 | 0.9744 | 0.9733 | 0.9759 | 0.3495 | 6.8280 |
| power_avg_uW | typical | 24.0000 | 20.0000 | 0.9751 | 0.9739 | 0.9761 | 0.3480 | 6.9386 |
| power_avg_uW | typical | 48.0000 | 20.0000 | 0.9742 | 0.9723 | 0.9777 | 0.3547 | 6.8865 |
