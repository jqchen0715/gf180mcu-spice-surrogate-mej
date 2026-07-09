# Data and Code Availability

The primary SPICE dataset, validation SPICE dataset, SPICE-generation scripts,
experiment scripts, generated result summaries, figure-generation scripts, and
SPICE netlists/logs supporting the manuscript are available in the archived
Zenodo repository:

```text
https://doi.org/10.5281/zenodo.20524583
```

The live GitHub repository is:

```text
https://github.com/jqchen0715/gf180mcu-spice-surrogate-mej
```

The revised SCI experiments add the `results/sci_revision/` directory and
the scripts `experiments/sci_revision_enhanced_evaluation.py` and
`experiments/plot_sci_revision_checks.py`. Before final manuscript
resubmission, a new GitHub release should be archived on Zenodo so the
repository DOI points to a package containing these files.

The repository includes:

- `data/dataset_v2_spice_320.csv`
- `data/dataset_v3_spice_480.csv`
- `spice_v2/generate_spice_dataset.py`
- `spice_v2/netlists/`
- `spice_v2/logs/`
- `spice_v2/netlists_v3_480/`
- `spice_v2/logs_v3_480/`
- `experiments/`
- `results/`
- `manuscript/figures/`
- `manuscript/sci_resubmission_rebuilt.tex`
- `manuscript/sci_resubmission_rebuilt.pdf`
- `manuscript_audits/`

The GF180MCU PDK checkout is not redistributed. The manuscript cites the
official repositories and reports the exact local PDK commit and model-file
provenance used for the simulations.
