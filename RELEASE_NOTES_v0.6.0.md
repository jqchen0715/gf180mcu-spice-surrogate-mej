# v0.6.0: Prospective stopping confirmation

Release date: 2026-07-18

Version DOI: https://doi.org/10.5281/zenodo.21425560

GitHub tag: https://github.com/jqchen0715/gf180mcu-spice-surrogate-mej/tree/v0.6.0

## Main additions

- estimator randomness fixed across support budgets, with the locked rule
  unchanged after recomputation;
- six new prospective seed-5 pools and 576 successful SPICE calls;
- precommit source/rule hashes and decision snapshots written before reference
  completion;
- separation of genuinely early-stopped pools from 96-call fallbacks;
- exact descriptive binomial intervals, stopping-signal ablations, and a
  400-rule threshold sensitivity audit;
- per-variant R2, MAE/NMAE, P95 and maximum absolute errors, ranking metrics,
  and explicit narrow-range failure cases;
- SPICE-call/time and model-overhead cost ledger;
- rebuilt 28-page manuscript, cover letter, prior-review action matrix, updated
  figures, and four passing numeric audits.

The release records four 80-call prospective stops and two 96-call fallbacks.
All six prospective pools remain within 0.02 pooled delay R2 of their measured
96-point references. The complete evidence package contains 10,669 successful
SPICE calls.
