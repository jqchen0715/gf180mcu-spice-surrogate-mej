# GF180MCU SPICE Surrogate Reproducibility Package

This repository contains the data, scripts, result summaries, generated figures,
and provenance notes supporting the Microelectronics Journal manuscript:

**A Source-Aware SPICE-Grounded Workflow for Sample-Efficient GF180MCU
Standard-Cell Exploration**

The study targets early design-space exploration for controlled transistor-level
standard-cell topologies in GF180MCU using ngspice. It is not a sign-off flow,
not a production standard-cell library generator, and not a full Liberty
characterization package.

## Contents

```text
data/
  dataset_v2_spice_320.csv       Primary GF180MCU/ngspice dataset
  dataset_v3_spice_480.csv       Independent validation dataset

experiments/
  v2_baseline_transfer.py
  source_aware_ablation.py
  v2_active_learning.py
  v2_model_diagnostics.py
  v2_robustness_ablation.py
  v3_scale_and_corner_support.py
  plot_*.py

results/
  source_aware/
  v2/
  v2_active_learning/
  v2_diagnostics/
  v2_robustness/
  v3_robustness/
  v3_scale_validation/

manuscript/figures/
  Figure PDFs and PNGs used in the manuscript

spice_v2/
  generate_spice_dataset.py
  schema.md
  status.md
  netlists/
  logs/
  netlists_v3_480/
  logs_v3_480/

tools/
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

Run the publication-facing checks and experiments from the repository root:

```bash
python tools/check_manuscript_numbers.py
python experiments/v2_robustness_ablation.py
python experiments/v3_scale_and_corner_support.py
```

For the full reproduction workflow, see:

```text
REPRODUCIBILITY.md
```

## Main Datasets

The V2 primary dataset contains 320 successful GF180MCU/ngspice rows:

| Cell | Rows |
|---|---:|
| INV | 80 |
| NAND2 | 80 |
| NOR2 | 80 |
| XOR2 | 80 |

The V3 validation dataset contains 480 successful GF180MCU/ngspice rows:

| Cell | Rows |
|---|---:|
| INV | 120 |
| NAND2 | 120 |
| NOR2 | 120 |
| XOR2 | 120 |

The V3 dataset is balanced across process corners: 160 `ff` rows, 160 `ss`
rows, and 160 `typical` rows, with 40 rows per cell-corner pair.

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

The live GitHub repository is:

```text
https://github.com/jqchen0715/gf180mcu-spice-surrogate-mej
```
