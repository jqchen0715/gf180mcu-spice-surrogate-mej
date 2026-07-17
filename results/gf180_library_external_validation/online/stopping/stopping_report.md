# Validation-blind stopping rule

Selection status: `development_constraints_satisfied`.

Locked rule: `{"coverage_ratio_threshold": 0.5, "minimum_budget": 64, "prediction_change_threshold": 0.05, "prequential_nmae_threshold": 0.25}`.

The rule uses only prequential delay error, model prediction change, and feature-space coverage. Seeds 0--2 were used for threshold development; seeds 3--4 were held back for confirmation.

## Confirmation result

- Median stop budget: 88/96.
- Median query reduction: 8.3%.
- Gap <= 0.02 success rate: 0.833.
- Median gap to full reference: 0.0000.
- Maximum gap to full reference: 0.0207.
