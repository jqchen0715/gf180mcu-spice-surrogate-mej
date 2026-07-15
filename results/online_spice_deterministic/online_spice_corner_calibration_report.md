# Simulator-in-the-Loop Corner Calibration Report

## Protocol

- Primary V2 rows: 320.
- Independent validation V3 rows: 480.
- Seeds: 0, 1, 2, 3, 4.
- Held-out corners: ff, ss, typical.
- Candidate points per cell and corner: 24.
- Maximum same-corner SPICE queries per run: 48.
- Every selected query launched ngspice and retained a netlist and log.
- V3 labels were used only to evaluate each budget and were not available to acquisition strategies.
- The acquisition loop did not use V3 metrics as a stopping or selection signal.
- Study thresholds: delay R2 >= 0.75; top-20% recall >= 0.90.

## Budget Trajectories

| heldout_corner | strategy | spice_queries | runs | median_delay_r2 | median_worst_cell_delay_r2 | median_top20_recall | median_cumulative_spice_wall_time_s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ff | cell_balanced_random | 0 | 5 | 0.3055 | -0.1887 | 0.8750 | 0.0000 |
| ff | cell_balanced_random | 12 | 5 | 0.7011 | 0.3683 | 0.8750 | 7.2145 |
| ff | cell_balanced_random | 24 | 5 | 0.7812 | 0.6055 | 0.8750 | 14.3748 |
| ff | cell_balanced_random | 36 | 5 | 0.8452 | 0.7107 | 0.9062 | 21.6261 |
| ff | cell_balanced_random | 48 | 5 | 0.8824 | 0.7821 | 0.8750 | 28.9154 |
| ff | cell_balanced_space_filling | 0 | 5 | 0.3055 | -0.1887 | 0.8750 | 0.0000 |
| ff | cell_balanced_space_filling | 12 | 5 | 0.6662 | 0.3822 | 0.8750 | 7.2443 |
| ff | cell_balanced_space_filling | 24 | 5 | 0.7763 | 0.6000 | 0.8750 | 14.3969 |
| ff | cell_balanced_space_filling | 36 | 5 | 0.8507 | 0.6528 | 0.8750 | 21.6534 |
| ff | cell_balanced_space_filling | 48 | 5 | 0.8797 | 0.7883 | 0.8750 | 28.8759 |
| ff | random | 0 | 5 | 0.3055 | -0.1887 | 0.8750 | 0.0000 |
| ff | random | 12 | 5 | 0.6357 | 0.2033 | 0.8750 | 7.4363 |
| ff | random | 24 | 5 | 0.7625 | 0.3611 | 0.8750 | 15.0535 |
| ff | random | 36 | 5 | 0.8526 | 0.6957 | 0.8750 | 23.0569 |
| ff | random | 48 | 5 | 0.8765 | 0.7701 | 0.8750 | 30.8412 |
| ff | space_filling | 0 | 5 | 0.3055 | -0.1887 | 0.8750 | 0.0000 |
| ff | space_filling | 12 | 5 | 0.6028 | 0.1620 | 0.8750 | 7.3980 |
| ff | space_filling | 24 | 5 | 0.7574 | 0.4450 | 0.8750 | 15.3320 |
| ff | space_filling | 36 | 5 | 0.8547 | 0.7284 | 0.8750 | 23.2998 |
| ff | space_filling | 48 | 5 | 0.8799 | 0.7938 | 0.8750 | 30.9867 |
| ff | uncertainty | 0 | 5 | 0.3055 | -0.1887 | 0.8750 | 0.0000 |
| ff | uncertainty | 12 | 5 | 0.5884 | 0.3885 | 0.9062 | 8.1856 |
| ff | uncertainty | 24 | 5 | 0.7078 | 0.5168 | 0.8750 | 15.2950 |
| ff | uncertainty | 36 | 5 | 0.7930 | 0.6868 | 0.9062 | 23.3377 |
| ff | uncertainty | 48 | 5 | 0.8511 | 0.7893 | 0.9062 | 31.0889 |
| ss | cell_balanced_random | 0 | 5 | 0.4825 | 0.3112 | 0.9688 | 0.0000 |
| ss | cell_balanced_random | 12 | 5 | 0.6136 | 0.4657 | 0.9688 | 7.1847 |
| ss | cell_balanced_random | 24 | 5 | 0.7616 | 0.6390 | 0.9062 | 14.3370 |
| ss | cell_balanced_random | 36 | 5 | 0.8144 | 0.7289 | 0.9375 | 21.6044 |
| ss | cell_balanced_random | 48 | 5 | 0.8251 | 0.7348 | 0.9375 | 28.7616 |
| ss | cell_balanced_space_filling | 0 | 5 | 0.4825 | 0.3112 | 0.9688 | 0.0000 |
| ss | cell_balanced_space_filling | 12 | 5 | 0.6946 | 0.5395 | 0.9688 | 7.2078 |
| ss | cell_balanced_space_filling | 24 | 5 | 0.8035 | 0.7060 | 0.9688 | 14.3782 |
| ss | cell_balanced_space_filling | 36 | 5 | 0.8514 | 0.7984 | 0.9688 | 21.5953 |
| ss | cell_balanced_space_filling | 48 | 5 | 0.8488 | 0.7925 | 0.9688 | 28.8618 |
| ss | random | 0 | 5 | 0.4825 | 0.3112 | 0.9688 | 0.0000 |
| ss | random | 12 | 5 | 0.5959 | 0.4013 | 0.9688 | 7.4319 |
| ss | random | 24 | 5 | 0.7151 | 0.5623 | 0.9688 | 14.6472 |
| ss | random | 36 | 5 | 0.7186 | 0.5963 | 0.9688 | 22.0406 |
| ss | random | 48 | 5 | 0.7800 | 0.6612 | 0.9688 | 29.7834 |
| ss | space_filling | 0 | 5 | 0.4825 | 0.3112 | 0.9688 | 0.0000 |
| ss | space_filling | 12 | 5 | 0.7927 | 0.6864 | 0.9688 | 7.2878 |
| ss | space_filling | 24 | 5 | 0.8071 | 0.7104 | 0.9688 | 14.6369 |
| ss | space_filling | 36 | 5 | 0.8213 | 0.7295 | 0.9688 | 23.2769 |
| ss | space_filling | 48 | 5 | 0.8142 | 0.7425 | 0.9688 | 30.8523 |
| ss | uncertainty | 0 | 5 | 0.4825 | 0.3112 | 0.9688 | 0.0000 |
| ss | uncertainty | 12 | 5 | 0.7555 | 0.6316 | 0.9062 | 7.7090 |
| ss | uncertainty | 24 | 5 | 0.7613 | 0.6259 | 0.9062 | 15.5476 |
| ss | uncertainty | 36 | 5 | 0.7741 | 0.7002 | 0.9375 | 23.7543 |
| ss | uncertainty | 48 | 5 | 0.7805 | 0.7087 | 0.9375 | 32.3858 |
| typical | cell_balanced_random | 0 | 5 | 0.7877 | 0.4872 | 0.8125 | 0.0000 |
| typical | cell_balanced_random | 12 | 5 | 0.7646 | 0.6193 | 0.8438 | 7.1822 |
| typical | cell_balanced_random | 24 | 5 | 0.7877 | 0.6381 | 0.9062 | 14.3298 |
| typical | cell_balanced_random | 36 | 5 | 0.8254 | 0.6792 | 0.9062 | 21.5837 |
| typical | cell_balanced_random | 48 | 5 | 0.8532 | 0.7387 | 0.9375 | 28.7457 |
| typical | cell_balanced_space_filling | 0 | 5 | 0.7877 | 0.4872 | 0.8125 | 0.0000 |
| typical | cell_balanced_space_filling | 12 | 5 | 0.8194 | 0.6462 | 0.8125 | 7.2171 |
| typical | cell_balanced_space_filling | 24 | 5 | 0.8896 | 0.7755 | 0.8750 | 14.4012 |
| typical | cell_balanced_space_filling | 36 | 5 | 0.8929 | 0.8074 | 0.8750 | 21.6220 |
| typical | cell_balanced_space_filling | 48 | 5 | 0.8887 | 0.7983 | 0.9062 | 28.8749 |
| typical | random | 0 | 5 | 0.7877 | 0.4872 | 0.8125 | 0.0000 |
| typical | random | 12 | 5 | 0.7813 | 0.6309 | 0.8438 | 7.3442 |
| typical | random | 24 | 5 | 0.8191 | 0.7260 | 0.8750 | 14.5128 |
| typical | random | 36 | 5 | 0.8555 | 0.7018 | 0.8750 | 21.4460 |
| typical | random | 48 | 5 | 0.8760 | 0.8085 | 0.9062 | 29.8327 |
| typical | space_filling | 0 | 5 | 0.7877 | 0.4872 | 0.8125 | 0.0000 |
| typical | space_filling | 12 | 5 | 0.8095 | 0.6444 | 0.8125 | 6.8821 |
| typical | space_filling | 24 | 5 | 0.8557 | 0.7020 | 0.8750 | 14.1813 |
| typical | space_filling | 36 | 5 | 0.8753 | 0.7611 | 0.8750 | 21.9313 |
| typical | space_filling | 48 | 5 | 0.8861 | 0.7987 | 0.9062 | 30.0133 |
| typical | uncertainty | 0 | 5 | 0.7877 | 0.4872 | 0.8125 | 0.0000 |
| typical | uncertainty | 12 | 5 | 0.7564 | 0.4448 | 0.9375 | 8.2285 |
| typical | uncertainty | 24 | 5 | 0.7460 | 0.5272 | 0.9375 | 15.2673 |
| typical | uncertainty | 36 | 5 | 0.7817 | 0.6652 | 0.9375 | 23.0989 |
| typical | uncertainty | 48 | 5 | 0.8086 | 0.7185 | 0.9062 | 32.0868 |

## Threshold Crossings

| heldout_corner | strategy | threshold | runs | reached_runs | median_queries | median_wall_time_s | query_reduction_vs_random_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ff | cell_balanced_random | delay_r2 | 5 | 5 | 16.0000 | 9.6838 | 33.3333 |
| ff | cell_balanced_random | joint | 5 | 3 | 16.0000 | 9.6685 |  |
| ff | cell_balanced_random | top20_recall | 5 | 4 | 2.0000 | 1.1908 |  |
| ff | cell_balanced_space_filling | delay_r2 | 5 | 5 | 24.0000 | 14.3949 | 0.0000 |
| ff | cell_balanced_space_filling | joint | 5 | 2 | 28.0000 | 16.8812 |  |
| ff | cell_balanced_space_filling | top20_recall | 5 | 4 | 8.0000 | 4.8791 |  |
| ff | random | delay_r2 | 5 | 5 | 24.0000 | 15.5370 | 0.0000 |
| ff | random | joint | 5 | 2 | 38.0000 | 23.8312 |  |
| ff | random | top20_recall | 5 | 3 | 0.0000 | 0.0000 |  |
| ff | space_filling | delay_r2 | 5 | 5 | 24.0000 | 14.2745 | 0.0000 |
| ff | space_filling | joint | 5 | 3 | 36.0000 | 22.7797 |  |
| ff | space_filling | top20_recall | 5 | 5 | 4.0000 | 1.8527 |  |
| ff | uncertainty | delay_r2 | 5 | 5 | 32.0000 | 20.7415 | -33.3333 |
| ff | uncertainty | joint | 5 | 4 | 32.0000 | 20.4382 |  |
| ff | uncertainty | top20_recall | 5 | 5 | 8.0000 | 5.0787 |  |
| ss | cell_balanced_random | delay_r2 | 5 | 5 | 24.0000 | 14.3370 |  |
| ss | cell_balanced_random | joint | 5 | 5 | 24.0000 | 14.3370 |  |
| ss | cell_balanced_random | top20_recall | 5 | 5 | 0.0000 | 0.0000 |  |
| ss | cell_balanced_space_filling | delay_r2 | 5 | 4 | 18.0000 | 10.7042 |  |
| ss | cell_balanced_space_filling | joint | 5 | 4 | 18.0000 | 10.7042 |  |
| ss | cell_balanced_space_filling | top20_recall | 5 | 5 | 0.0000 | 0.0000 |  |
| ss | random | delay_r2 | 5 | 3 | 32.0000 | 24.1996 |  |
| ss | random | joint | 5 | 3 | 32.0000 | 24.1996 |  |
| ss | random | top20_recall | 5 | 5 | 0.0000 | 0.0000 |  |
| ss | space_filling | delay_r2 | 5 | 5 | 12.0000 | 7.1101 |  |
| ss | space_filling | joint | 5 | 5 | 12.0000 | 7.2878 |  |
| ss | space_filling | top20_recall | 5 | 5 | 0.0000 | 0.0000 |  |
| ss | uncertainty | delay_r2 | 5 | 5 | 12.0000 | 7.7090 |  |
| ss | uncertainty | joint | 5 | 5 | 16.0000 | 13.4286 |  |
| ss | uncertainty | top20_recall | 5 | 5 | 0.0000 | 0.0000 |  |
| typical | cell_balanced_random | delay_r2 | 5 | 5 | 0.0000 | 0.0000 |  |
| typical | cell_balanced_random | joint | 5 | 5 | 16.0000 | 9.6298 | 55.5556 |
| typical | cell_balanced_random | top20_recall | 5 | 5 | 16.0000 | 9.6298 | 55.5556 |
| typical | cell_balanced_space_filling | delay_r2 | 5 | 5 | 0.0000 | 0.0000 |  |
| typical | cell_balanced_space_filling | joint | 5 | 5 | 40.0000 | 23.9218 | -11.1111 |
| typical | cell_balanced_space_filling | top20_recall | 5 | 5 | 40.0000 | 23.9218 | -11.1111 |
| typical | random | delay_r2 | 5 | 5 | 0.0000 | 0.0000 |  |
| typical | random | joint | 5 | 5 | 36.0000 | 23.5473 | 0.0000 |
| typical | random | top20_recall | 5 | 5 | 36.0000 | 23.5473 | 0.0000 |
| typical | space_filling | delay_r2 | 5 | 5 | 0.0000 | 0.0000 |  |
| typical | space_filling | joint | 5 | 5 | 20.0000 | 11.8249 | 44.4444 |
| typical | space_filling | top20_recall | 5 | 5 | 20.0000 | 11.8249 | 44.4444 |
| typical | uncertainty | delay_r2 | 5 | 5 | 0.0000 | 0.0000 |  |
| typical | uncertainty | joint | 5 | 5 | 12.0000 | 8.7804 | 66.6667 |
| typical | uncertainty | top20_recall | 5 | 5 | 4.0000 | 3.3614 | 88.8889 |

## Paired Two-Sided Wilcoxon Tests

| budget | metric | baseline | pairs | median_proposed | median_baseline | median_difference | matched_rank_biserial | wilcoxon_statistic | p_raw | p_holm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 24 | delay_r2 | random | 15 | 0.8119 | 0.7625 | 0.0478 | 0.6667 | 20.0000 | 0.0215 | 0.0646 |
| 24 | delay_r2 | cell_balanced_random | 15 | 0.8119 | 0.7812 | 0.0290 | 0.4000 | 36.0000 | 0.1876 | 0.3752 |
| 24 | delay_r2 | space_filling | 15 | 0.8119 | 0.8114 | 0.0015 | 0.3167 | 41.0000 | 0.3028 | 0.3752 |
| 24 | delay_r2 | uncertainty | 15 | 0.8119 | 0.7232 | 0.1105 | 0.8000 | 12.0000 | 0.0043 | 0.0171 |
| 24 | worst_cell_delay_r2 | random | 15 | 0.6785 | 0.5990 | 0.0877 | 0.6333 | 22.0000 | 0.0302 | 0.0905 |
| 24 | worst_cell_delay_r2 | cell_balanced_random | 15 | 0.6785 | 0.6331 | 0.0133 | 0.3333 | 40.0000 | 0.2769 | 0.4155 |
| 24 | worst_cell_delay_r2 | space_filling | 15 | 0.6785 | 0.6888 | 0.0622 | 0.3833 | 37.0000 | 0.2078 | 0.4155 |
| 24 | worst_cell_delay_r2 | uncertainty | 15 | 0.6785 | 0.5460 | 0.1692 | 0.7333 | 16.0000 | 0.0103 | 0.0410 |
| 24 | top20_recall | random | 15 | 0.8750 | 0.8750 | 0.0000 | 0.4722 | 9.5000 | 0.2217 | 0.8867 |
| 24 | top20_recall | cell_balanced_random | 15 | 0.8750 | 0.9062 | 0.0000 | 0.1515 | 28.0000 | 0.6533 | 1.0000 |
| 24 | top20_recall | space_filling | 15 | 0.8750 | 0.9062 | 0.0000 | -0.3111 | 15.5000 | 0.3916 | 1.0000 |
| 24 | top20_recall | uncertainty | 15 | 0.8750 | 0.9062 | 0.0000 | -0.1273 | 24.0000 | 0.7174 | 1.0000 |
| 48 | delay_r2 | random | 15 | 0.8729 | 0.8564 | 0.0233 | 0.7167 | 17.0000 | 0.0125 | 0.0374 |
| 48 | delay_r2 | cell_balanced_random | 15 | 0.8729 | 0.8685 | 0.0094 | 0.1667 | 50.0000 | 0.5995 | 1.0000 |
| 48 | delay_r2 | space_filling | 15 | 0.8729 | 0.8674 | 0.0003 | -0.0167 | 59.0000 | 0.9780 | 1.0000 |
| 48 | delay_r2 | uncertainty | 15 | 0.8729 | 0.8111 | 0.0502 | 0.7500 | 15.0000 | 0.0084 | 0.0334 |
| 48 | worst_cell_delay_r2 | random | 15 | 0.7885 | 0.7120 | 0.0640 | 0.6167 | 23.0000 | 0.0353 | 0.1414 |
| 48 | worst_cell_delay_r2 | cell_balanced_random | 15 | 0.7885 | 0.7674 | 0.0099 | 0.2333 | 46.0000 | 0.4543 | 0.9086 |
| 48 | worst_cell_delay_r2 | space_filling | 15 | 0.7885 | 0.7938 | 0.0038 | 0.0000 | 60.0000 | 1.0000 | 1.0000 |
| 48 | worst_cell_delay_r2 | uncertainty | 15 | 0.7885 | 0.7255 | 0.0509 | 0.5333 | 28.0000 | 0.0730 | 0.2190 |
| 48 | top20_recall | random | 15 | 0.9375 | 0.9062 | 0.0000 | 0.7143 | 4.0000 | 0.0829 | 0.3315 |
| 48 | top20_recall | cell_balanced_random | 15 | 0.9375 | 0.9375 | 0.0000 | 0.2778 | 13.0000 | 0.4705 | 0.9410 |
| 48 | top20_recall | space_filling | 15 | 0.9375 | 0.9062 | 0.0000 | 0.2000 | 18.0000 | 0.5637 | 0.9410 |
| 48 | top20_recall | uncertainty | 15 | 0.9375 | 0.9062 | 0.0000 | 0.4167 | 10.5000 | 0.2714 | 0.8142 |

## Claim Boundary

This experiment establishes a genuine ngspice-in-the-loop calibration study within the same GF180MCU model and simulator flow. It does not establish cross-PDK, cross-simulator, layout-extracted, or complete Liberty characterization performance.
