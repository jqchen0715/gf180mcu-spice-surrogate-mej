# SKY130 external cross-PDK protocol replication

The stopping rule was copied unchanged from the GF180MCU development study. No SKY130 label or trajectory was used to select or tune its thresholds.

Locked rule: `{"coverage_ratio_threshold": 0.5, "minimum_budget": 64, "prediction_change_threshold": 0.05, "prequential_nmae_threshold": 0.25}`.

- Independent pools: 15.
- Median stop budget: 80/96.
- Median query reduction: 16.7%.
- Gap <= 0.02 success rate: 1.000.
- Gap <= 0.05 success rate: 1.000.
- Median delay R2 gap to full reference: 0.0000.
- Maximum delay R2 gap to full reference: 0.0110.

This is a protocol-replication result with PDK-specific retraining, not zero-shot transfer of a GF180MCU regression model to SKY130.
