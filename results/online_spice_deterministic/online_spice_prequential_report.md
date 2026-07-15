# Validation-Blind Prequential Diagnostics

Each batch was predicted before its SPICE labels were added. V3 labels were merged only after replay to assess diagnostic validity.

## Budget Summary

| heldout_corner | support_budget | runs | median_prequential_delay_mae_ns | median_rolling_delay_mae_ns | median_external_delay_r2 | median_external_worst_cell_delay_r2 |
| --- | --- | --- | --- | --- | --- | --- |
| ff | 4 | 5 | 0.1444 | 0.1444 | 0.4110 | -0.0315 |
| ff | 8 | 5 | 0.0837 | 0.1242 | 0.5557 | 0.1664 |
| ff | 12 | 5 | 0.1172 | 0.1093 | 0.6662 | 0.3822 |
| ff | 16 | 5 | 0.0583 | 0.0878 | 0.6979 | 0.4297 |
| ff | 20 | 5 | 0.0911 | 0.0931 | 0.7497 | 0.5356 |
| ff | 24 | 5 | 0.0826 | 0.1036 | 0.7763 | 0.6000 |
| ff | 28 | 5 | 0.0793 | 0.0812 | 0.8254 | 0.6012 |
| ff | 32 | 5 | 0.0443 | 0.0621 | 0.8282 | 0.6162 |
| ff | 36 | 5 | 0.0598 | 0.0466 | 0.8507 | 0.6528 |
| ff | 40 | 5 | 0.0509 | 0.0543 | 0.8724 | 0.7566 |
| ff | 44 | 5 | 0.0389 | 0.0497 | 0.8758 | 0.7669 |
| ff | 48 | 5 | 0.0518 | 0.0401 | 0.8797 | 0.7883 |
| ss | 4 | 5 | 0.1118 | 0.1118 | 0.5403 | 0.3790 |
| ss | 8 | 5 | 0.1050 | 0.1520 | 0.6658 | 0.4870 |
| ss | 12 | 5 | 0.1166 | 0.1439 | 0.6946 | 0.5395 |
| ss | 16 | 5 | 0.0441 | 0.0945 | 0.7413 | 0.6348 |
| ss | 20 | 5 | 0.0775 | 0.0703 | 0.7383 | 0.6382 |
| ss | 24 | 5 | 0.1242 | 0.0901 | 0.8035 | 0.7060 |
| ss | 28 | 5 | 0.1112 | 0.1039 | 0.8096 | 0.7265 |
| ss | 32 | 5 | 0.0549 | 0.0859 | 0.8280 | 0.7773 |
| ss | 36 | 5 | 0.0631 | 0.0579 | 0.8514 | 0.7984 |
| ss | 40 | 5 | 0.0487 | 0.0704 | 0.8457 | 0.7873 |
| ss | 44 | 5 | 0.0611 | 0.0776 | 0.8500 | 0.7970 |
| ss | 48 | 5 | 0.0603 | 0.0558 | 0.8488 | 0.7925 |
| typical | 4 | 5 | 0.0910 | 0.0910 | 0.7635 | 0.6462 |
| typical | 8 | 5 | 0.0537 | 0.0742 | 0.7937 | 0.6033 |
| typical | 12 | 5 | 0.0827 | 0.0879 | 0.8194 | 0.6462 |
| typical | 16 | 5 | 0.1331 | 0.0896 | 0.8488 | 0.7583 |
| typical | 20 | 5 | 0.0549 | 0.0873 | 0.8339 | 0.7248 |
| typical | 24 | 5 | 0.0574 | 0.0680 | 0.8896 | 0.7755 |
| typical | 28 | 5 | 0.0358 | 0.0480 | 0.8910 | 0.7813 |
| typical | 32 | 5 | 0.0295 | 0.0326 | 0.8812 | 0.7681 |
| typical | 36 | 5 | 0.0591 | 0.0398 | 0.8929 | 0.8074 |
| typical | 40 | 5 | 0.0402 | 0.0606 | 0.8978 | 0.8051 |
| typical | 44 | 5 | 0.0520 | 0.0476 | 0.8848 | 0.8097 |
| typical | 48 | 5 | 0.0534 | 0.0557 | 0.8887 | 0.7983 |

## Correlation With Independent V3 Performance

| internal_metric | external_metric | pairs | spearman_rho | p_value |
| --- | --- | --- | --- | --- |
| prequential_delay_mae_ns | external_delay_r2 | 180 | -0.3869 | 0.0000 |
| prequential_delay_mae_ns | external_worst_cell_delay_r2 | 180 | -0.3352 | 0.0000 |
| prequential_delay_mape_pct | external_delay_r2 | 180 | -0.3385 | 0.0000 |
| prequential_delay_mape_pct | external_worst_cell_delay_r2 | 180 | -0.3886 | 0.0000 |
| prequential_power_mae_uW | external_delay_r2 | 180 | -0.2692 | 0.0003 |
| prequential_power_mae_uW | external_worst_cell_delay_r2 | 180 | -0.2682 | 0.0003 |
