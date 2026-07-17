# SKY130 cross-PDK numeric audit

Overall status: **PASS**.

## Evidence counts

- Primary dataset: 576 successful rows.
- Independent validation dataset: 576 successful rows.
- Online external-replication calls: 1440 successful rows in 15 pools.
- SKY130 publication evidence added: 2,592 SPICE calls.
- Complete two-PDK evidence package: 10,093 SPICE calls.

## Locked-rule result

- Median stop budget: 80/96.
- Median query reduction: 16.7%.
- Runs within 0.02: 15/15.
- Maximum delay R2 gap: 0.014627.

## Checks

- [x] primary_576_all_ok
- [x] validation_576_all_ok
- [x] sixteen_variants_each_dataset
- [x] eight_families_each_dataset
- [x] balanced_corner_counts
- [x] fifteen_complete_online_pools
- [x] online_all_ok
- [x] online_unique_sample_ids
- [x] candidate_features_1440
- [x] trajectory_15_by_7_budgets
- [x] locked_rule_unchanged
- [x] sky130_not_used_for_rule_selection
- [x] locked_rule_15_runs
- [x] all_locked_gaps_le_0p02
- [x] all_locked_gaps_le_0p05
