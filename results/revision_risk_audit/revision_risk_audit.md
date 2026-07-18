# Revision-risk audit

Estimator randomness is fixed to the pool seed at every support budget. The previously locked three-signal rule remains unchanged.

## Conditional stopping result

```text
     pdk               cohort                   method               subset  runs  successful_runs  gap_le_0p02_rate  exact_95ci_lower  exact_95ci_upper  median_stop_budget  median_query_reduction_pct  median_gap_to_full  maximum_gap_to_full  median_worst_family_r2  median_worst_variant_r2
GF180MCU         confirmation locked_three_signal_rule             all_runs     6                5          0.833333          0.358765          0.995789                88.0                    8.333333            0.000000             0.022629                0.738864                 0.469665
GF180MCU         confirmation locked_three_signal_rule      early_stop_only     3                2          0.666667          0.094299          0.991596                80.0                   16.666667            0.018421             0.022629                0.640877                 0.412969
GF180MCU         confirmation locked_three_signal_rule full_budget_fallback     3                3          1.000000          0.292402          1.000000                96.0                    0.000000            0.000000             0.000000                0.739377                 0.526361
  SKY130 external_replication locked_three_signal_rule             all_runs    15               15          1.000000          0.781981          1.000000                80.0                   16.666667            0.000000             0.010960                0.700366                 0.171002
  SKY130 external_replication locked_three_signal_rule      early_stop_only     8                8          1.000000          0.630583          1.000000                80.0                   16.666667            0.004421             0.010960                0.689924                 0.010531
  SKY130 external_replication locked_three_signal_rule full_budget_fallback     7                7          1.000000          0.590384          1.000000                96.0                    0.000000            0.000000             0.000000                0.758625                 0.499374
```

The GF180MCU development grid contained 400 rules; 238 met the prespecified development constraints. This is a sensitivity count, not additional confirmation evidence.

## Interpretation limits

- Exact binomial intervals are descriptive because corner pools sharing a seed and PDK are not fully independent.
- Cumulative SPICE time is the sum of per-call engine times, not elapsed time under parallel execution.
- Negative per-variant R2 can coexist with modest absolute error when a variant has a narrow delay range.
- Released-pool analyses replay stopping over completed measured pools; prospective confirmation is reported separately.
