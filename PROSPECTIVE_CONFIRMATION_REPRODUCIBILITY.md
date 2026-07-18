# Prospective Locked-Rule Confirmation

## Purpose

The completed GF180MCU and SKY130 pools permit matched stopping replay, but the
chronology of a real stop is stronger evidence. This stage freezes the existing
GF180MCU rule and runs one new seed-5 pool per corner and PDK. The independent
validation file is not opened until a decision record exists.

## Frozen rule

```text
minimum budget:                 64
prequential NMAE threshold:     0.25
prediction-change threshold:    0.05
coverage-radius threshold:      0.50
consecutive eligible batches:   2
batch size:                     16
candidate pool:                 96
estimator random state:         fixed to pool seed across budgets
```

## Command

From the repository root, with the exact GF180MCU and SKY130 PDK checkouts
documented elsewhere in this package:

```bash
python experiments/prospective_locked_rule_confirmation.py \
  --seed 5 --workers 8 --resume
```

The command is resumable. It does not overwrite an existing decision record.

## Chronological artifacts

Each directory below `results/prospective_locked_confirmation/{gf180,sky130}/`
contains:

- `precommit_manifest.json`: rule, source hashes, primary-data hash, and the
  declared-but-unopened validation path;
- `candidate_features.csv`: feature-only candidate pool and query order;
- `sequential_measurements.csv`: all measured rows, with stopping-evaluation
  and post-decision reference-completion phases distinguished;
- `online_observables.csv`: validation-blind stopping signals available at the
  decision;
- `decision_snapshot.csv`: the measured prefix visible at the decision;
- `decision_record.json`: timestamp, decision type/budget, observable values,
  and SHA-256 links;
- `reference_completion_record.json`: hash link from the prior decision to the
  completed reference;
- `post_decision_validation_trajectory.csv`: validation metrics computed only
  after the decision artifact exists;
- per-query ngspice netlists and logs.

## Results

| PDK | Pools | 80-call stops | 96-call fallbacks | Calls avoided at decision | Pools within 0.02 | Maximum gap |
|---|---:|---:|---:|---:|---:|---:|
| GF180MCU | 3 | 2 | 1 | 32 | 3/3 | 0.0154 |
| SKY130 | 3 | 2 | 1 | 32 | 3/3 | 0.0190 |

The combined outcome is 6/6 within the pooled delay-R2 gap criterion; the
genuinely early-stopped subset is 4/4. The exact descriptive 95% intervals are
0.541-1.000 and 0.398-1.000, respectively. These small-cohort intervals are not
population-level guarantees.

The study intentionally executes 64 post-decision calls to obtain the six
measured references. Those calls are evidence cost and are not information
available to the stopping algorithm; operational use would omit them.

## Audits

```bash
python experiments/revision_risk_audit.py
python tools/audit_revision_manuscript.py
```

The second command revalidates every decision-snapshot hash and row count,
recomputes the 10,669-call evidence total, and checks the manuscript tokens
against the structured results.
