Dear Editor-in-Chief,

Please consider our Research Article, “A Validation-Blind Simulator-in-the-Loop Stopping Protocol for Standard-Cell Delay Calibration Across Two Open PDKs,” for publication in *Microelectronics Journal*.

For transparency, this is a substantially rebuilt resubmission of manuscript MEJ-D-26-01024, which was rejected after external review. The present paper changes the unit of contribution from an offline machine-learning benchmark to a methods-validation study with fresh simulator calls, locked stopping rules, two released-cell PDKs, and a prospective decision-before-reference test. It is not a cosmetic revision of the rejected version.

The manuscript studies a practical design-automation question: whether a stopping protocol fixed on one open process design kit can reduce new SPICE support work on a second PDK without consulting validation labels or retuning its thresholds. The complete evidence package now contains 10,669 successful simulator calls across controlled data generation, online acquisition, measured references, released-standard-cell validation, cross-PDK replication, prospective confirmation, and a partial Liberty compatibility check.

The study makes three main contributions. First, it formulates unseen-corner calibration as a deterministic simulator-in-the-loop allocation problem in which every acquired label is obtained from a fresh ngspice run and validation labels remain isolated from stopping decisions. Second, it locks a validation-blind stopping rule on nine GF180MCU development pools and evaluates it on six untouched GF180MCU confirmation pools and 15 independently generated SKY130 pools, using PDK-specific retraining. Third, it runs six new seed-5 pools prospectively: code and rule hashes are committed before simulation, each stop decision and measurement snapshot is written before reference completion, and validation labels are opened only afterward.

With estimator randomness fixed across budgets, the locked rule remains within a prespecified pooled delay-R2 gap of 0.02 in 5/6 GF180MCU confirmation pools and 15/15 SKY130 pools. Conditional on genuine early stopping, the counts are 2/3 and 8/8; full-budget fallbacks are reported separately. In the new prospective cohort, four pools stop at 80, two fall back to 96, and all six satisfy the criterion, with a maximum gap of 0.0190. Exact descriptive intervals, stopping-signal ablations, model and SPICE cost accounting, ranking metrics, P95 errors, and per-variant failures are reported. In particular, negative R2 for narrow-range variants is disclosed to prevent a uniform cell-level claim.

We believe the manuscript fits the journal's scope in integrated-circuit design automation, microelectronic modeling, and AI-assisted design methodology. The claimed use is early transistor-level standard-cell delay exploration. We do not claim a new acquisition algorithm, zero-shot model transfer, a replacement for layout-extracted sign-off, or complete Liberty characterization.

The manuscript is original, is not under consideration elsewhere, and has been approved by all authors. The authors declare no competing interests and no specific funding support. The corresponding author is Jiaqing Chen.

Thank you for considering this work.

Sincerely,

Jiaqing Chen

Corresponding author

School of Integrated Circuit Science and Engineering, Beihang University

Jq_Chen0715@buaa.edu.cn
