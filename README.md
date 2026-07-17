# GF180MCU SPICE Surrogate Reproducibility Package

This repository contains the data, scripts, result summaries, generated figures,
and provenance notes supporting the deterministic simulator-in-the-loop manuscript:

**A Deterministic Simulator-in-the-Loop Protocol for Sample-Efficient GF180MCU
Standard-Cell Corner Calibration**

The study targets early design-space exploration for both controlled
transistor-level topologies and released GF180MCU standard-cell CDLs using
ngspice. It is not a sign-off flow, a production standard-cell library
generator, or a full Liberty characterization package.

## Current Main Evidence

The current study uses deterministic datasets with the GF180MCU global and
mismatch statistical switches explicitly disabled:

```text
data/dataset_primary_deterministic_320.csv
data/dataset_validation_deterministic_480.csv
```

The main simulator-in-the-loop outputs are under:

```text
results/online_spice_deterministic/
```

They contain 3600 successful online ngspice query records, validation-blind
budget trajectories, paired tests, repeated-query consistency checks, and 15
measured 96-point exhaustive references. The GitHub repository retains the
structured query and result records. The next Zenodo release should additionally
include the per-query netlists and logs listed in
`DETERMINISTIC_ONLINE_REPRODUCIBILITY.md`.

The released-library external validation is under:

```text
results/gf180_library_external_validation/
```

It contains two independent 576-row datasets, 15 completed 96-point online
pools (1440 fresh SPICE calls), a stopping rule locked on nine development
pools and tested on six untouched confirmation pools, and a 432-point partial
comparison with official Liberty delay surfaces. The 16 released-CDL variants
span eight combinational families and drive strengths 1 and 4. Exact commands,
PDK commits, and interpretation boundaries are documented in
`RELEASED_LIBRARY_REPRODUCIBILITY.md`.

The current manuscript and numeric audit are:

```text
manuscript/mej_deterministic_online_submission.tex
manuscript/mej_deterministic_online_submission.pdf
manuscript_audits/mej_deterministic_online_numeric_audit.md
```

## Contents

```text
data/
  dataset_primary_deterministic_320.csv
  dataset_validation_deterministic_480.csv
  dataset_v2_spice_320.csv       Primary GF180MCU/ngspice dataset
  dataset_v3_spice_480.csv       Independent validation dataset

experiments/
  online_spice_corner_calibration.py
  complete_online_exhaustive_reference.py
  replay_online_prequential_diagnostics.py
  tune_corner_acquisition_weight.py
  plot_deterministic_online_results.py
  generate_library_spice_datasets.py
  library_online_external_validation.py
  validate_library_online_stopping.py
  liberty_surface_crosscheck.py
  plot_official_library_validation.py
  sci_revision_enhanced_evaluation.py
  v2_baseline_transfer.py
  source_aware_ablation.py
  v2_active_learning.py
  v2_model_diagnostics.py
  v2_robustness_ablation.py
  v3_scale_and_corner_support.py
  plot_*.py

results/
  online_spice_deterministic/
  gf180_library_external_validation/
  deterministic_sci_revision/
  deterministic_v3_scale_validation/
  deterministic_robustness/
  source_aware/
  v2/
  v2_active_learning/
  v2_diagnostics/
  v2_robustness/
  v3_robustness/
  v3_scale_validation/
  sci_revision/

manuscript/figures/
  Figure PDFs and PNGs used in the manuscript

manuscript/
  mej_deterministic_online_submission.tex
  mej_deterministic_online_submission.pdf
  sci_resubmission_rebuilt.tex
  sci_resubmission_rebuilt.pdf
  microelectronics_journal_references.bib

spice_v2/
  generate_spice_dataset.py
  gf180_library_cells.py
  schema.md
  status.md
  netlists/
  logs/
  netlists_v3_480/
  logs_v3_480/

tools/
  audit_deterministic_online_manuscript.py
  check_manuscript_numbers.py

manuscript_audits/
  reference_link_audit.md
  manuscript_numeric_consistency_audit.md
```

The local GF180MCU PDK checkout is not redistributed here. Users should obtain
the PDK and primitive-library files from the official repositories cited in the
manuscript. The reported simulations used ngspice 46 and the GF180MCU primitive
model file `sm141064.ngspice`; the manuscript records the exact local PDK commit
used for the reported data.

## Quick Start

Create a Python environment and install the analysis dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Run the current publication-facing numeric audit from the repository root:

```bash
python tools/audit_deterministic_online_manuscript.py
python tools/audit_official_library_extension.py
```

For the deterministic data-generation and simulator-in-the-loop commands, see:

```text
DETERMINISTIC_ONLINE_REPRODUCIBILITY.md
RELEASED_LIBRARY_REPRODUCIBILITY.md
```

## Legacy Package Note

Files retaining the `v2` and `v3` names belong to the preceding reproducibility
package. They are kept for release history but are not the publication datasets
for the deterministic online extension.

## Reuse and Licensing

- Code is released under the MIT License; see `LICENSE`.
- Data, figures, result tables, and documentation are released under the
  Creative Commons Attribution 4.0 International License; see
  `DATA_LICENSE.md`.

## Citation

Please cite the archived Zenodo release:

```text
https://doi.org/10.5281/zenodo.20524583
```

The DOI above identifies the preceding archived package. Before submitting the
deterministic online manuscript, create a new GitHub release and a new Zenodo
version containing the files listed in
`DETERMINISTIC_ONLINE_REPRODUCIBILITY.md`.

The live GitHub repository is:

```text
https://github.com/jqchen0715/gf180mcu-spice-surrogate-mej
```
