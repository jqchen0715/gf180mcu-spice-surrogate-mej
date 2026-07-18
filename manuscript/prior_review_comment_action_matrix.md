# MEJ-D-26-01024 prior-review action matrix

This internal matrix maps every substantive point from the rejected version to
the rebuilt manuscript. It is not a claim that all limitations have disappeared;
where new evidence cannot close a point, the manuscript narrows the claim.

| ID | Prior concern | Revision evidence or action | Status |
|---|---|---|---|
| R1.1 | Limited novelty; conventional ML workflow | Repositioned as a methods-validation paper. The contribution is the validation-blind stopping evidence chain, fixed estimator randomness, conditional early-stop accounting, and prospective decision-before-reference confirmation—not a new regressor or acquisition theory. | Addressed by reframing and new evidence |
| R1.2 | Small 320/480-row data | Retained the controlled 320/480 stage only as an initial mechanism check. Added released GF180MCU and SKY130 primary/validation sets, 30 completed 96-call pools, six new prospective pools, and 10,669 successful calls. Finite-cohort limitations remain explicit. | Materially expanded; bounded |
| R1.3 | Missing GPR, XGBoost, LightGBM, CatBoost, GNN, etc. | Retained CatBoost/GPR same-flow sanity checks and citations to modern cell-library models. The paper explicitly does not make a model-ranking claim; expanding the model zoo would not test the stopping chronology. | Claim narrowed; rationale stated |
| R1.4 | Active learning was retrospective, not simulator-in-the-loop | Controlled acquisition obtains every support label from a fresh ngspice run. More importantly, six new seed-5 pools commit hashes, simulate batch-by-batch, write the decision snapshot, and only then complete the reference/open validation labels. | Directly addressed |
| R1.5 | Transfer covered only four cells in one PDK | Released stages cover eight combinational families, 16 variants, two drive strengths, three corners, and two open PDKs. PDK-specific retraining and per-variant metrics are explicit. | Directly addressed within pre-layout scope |
| R1.6 | GF180MCU-only evidence | Added 576+576 SKY130 primary/validation rows, 15 completed SKY130 pools, and three prospective SKY130 pools without threshold retuning. | Directly addressed |
| R1.7 | Little physical insight | Added a physical interpretation of corner-dependent delay, implicit threshold-voltage/model-section effects, power-versus-delay behavior, internal topology, and narrow-range negative R2. | Addressed |
| R1.8 | Missing uncertainty, worst-case, and tail analysis | Added exact success intervals, worst-family and worst-variant R2, per-variant MAE/NMAE, pooled P95 and maximum absolute error, and explicit counterexamples. | Directly addressed |
| R1.9 | Missing ranking metrics | Reports Spearman rho, Kendall tau/NDCG in the controlled stage, top-20% recall, pooled stopped-model ranking, and a 432-point Liberty rank check. | Directly addressed |
| R1.10 | Missing statistical tests | Matched Wilcoxon tests with Holm correction remain for acquisition comparisons; stopping proportions now include exact Clopper–Pearson intervals and dependence caveats. | Directly addressed |
| R1.11 | Hyperparameters unclear | Methods list 240-tree controlled and 320-tree released models, leaf size, feature policy, fixed random-state policy, software versions, and purpose. | Directly addressed |
| R1.12 | Categorical encoding unclear | Methods specify standardization and unknown-safe one-hot encoding for family, variant, arc, and corner. | Directly addressed |
| R1.13 | Computational cost unclear | Added call counts, cumulative per-call ngspice engine time, model fit/predict time, early-stop/fallback separation, and the distinction between operationally avoided and post-decision reference calls. | Directly addressed |
| R1.14 | Zero-shot corner deterioration unexplained | Added model- and device-level explanation: corner sections jointly shift threshold, mobility, capacitance, and drive; typical is easier to bracket, while ff/ss require same-corner support. | Addressed |
| R1.15 | Data imbalance | Released primary/validation data are balanced by 16 variants and three corners; online batches contain one query per variant. Counts and sampling seeds are reported. | Directly addressed |
| R1.16 | Validation used the same simulator/flow | Added released-topology GF180MCU and second-PDK SKY130 tests. The paper still uses ngspice 46 and explicitly states that cross-simulator/post-layout validation remains untested. | Expanded; residual limitation explicit |
| R1.17 | Reproducibility environment incomplete | Added exact PDK commits, ngspice version, Python and package versions, model/random-state settings, scripts, manifests, netlists, logs, checksums, and decision snapshots. | Directly addressed |
| R1.18 | Provenance benefit unclear | Provenance now verifies deterministic-mode control, chronological information boundaries, unchanged rules, and reference completion after decisions; it is tied to falsifiable audits rather than presented as bookkeeping. | Addressed |
| R2.1 | Transistor-only study does not justify broad early-exploration claims | Title/abstract/conclusion now say pre-layout standard-cell delay calibration. Released CDLs and partial Liberty comparison improve realism, but sign-off, layout, and full characterization claims are explicitly excluded. | Claim narrowed |
| R2.2 | Cell sizing/layout/characterization effort savings unclear | The revision quantifies only SPICE support calls and engine time. It does not claim layout or cell-height savings. | Claim narrowed; cost quantified |
| R2.3 | Slew/load inputs are known; novelty unclear | The manuscript agrees that the features are conventional. Novelty is the validation-blind stopping protocol and its chronological cross-PDK validation, not input selection. | Addressed by positioning |
| R2.4 | How is Vth incorporated? | Methods state that threshold voltage is implicit in each PDK corner-model section and is not an independently adjustable regressor feature; models are retrained per PDK. | Directly addressed |
| R2.5 | Cross-cell transfer unclear | Defines controlled cells, released families/variants, drive strengths, arcs, variant-balanced batches, family/variant features, and per-variant validation. No leave-one-cell-out claim is made. | Directly addressed/claim clarified |
| R2.6 | Data amount and overhead unclear | All dataset sizes, pool sizes, batch sizes, call totals, SPICE time, and model overhead are now tabulated or stated. | Directly addressed |
| R2.7 | Delay improves but power does not; explanation missing | Added a bounded physical explanation based on corner-sensitive drive current versus the sampled capacitive switching-energy regime; explicitly avoids claiming general corner-invariant power. | Addressed |
| R2.8 | Cell height, fixed length, ranges, and industrial temperature | Released-cell geometry is preserved from official cells; cell-height/layout optimization is out of scope. Controlled length remains fixed and identified. Released stages use -40 to 125 C, while wider/industrial qualification ranges remain a limitation. | Partly addressed; scope bounded |

## Required author actions before submission

1. Publish the prepared revision package as a new immutable GitHub/Zenodo release and replace the provisional data-availability sentence with its version-specific DOI.
2. Confirm whether the journal wants a formal point-by-point response for a new submission after rejection; if requested, convert this matrix into the journal response format without implying that the prior decision was a revision invitation.
3. Verify author approval, submission category, and the transparent reference to MEJ-D-26-01024 in the cover letter.
