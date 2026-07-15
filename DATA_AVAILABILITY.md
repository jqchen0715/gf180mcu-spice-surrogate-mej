# Data and Code Availability

The preceding static-table reproducibility package is archived at:

```text
https://doi.org/10.5281/zenodo.20524583
```

The live GitHub repository is:

```text
https://github.com/jqchen0715/gf180mcu-spice-surrogate-mej
```

The deterministic simulator-in-the-loop extension is prepared in this live
repository. Before manuscript submission, create a new GitHub release and a new
Zenodo version. The resulting version DOI should replace the preceding DOI in
the final manuscript.

The repository includes:

- `data/dataset_primary_deterministic_320.csv`
- `data/dataset_validation_deterministic_480.csv`
- `spice_v2/generate_spice_dataset.py`
- `experiments/online_spice_corner_calibration.py`
- `experiments/complete_online_exhaustive_reference.py`
- `experiments/replay_online_prequential_diagnostics.py`
- `results/online_spice_deterministic/`
- `manuscript/mej_deterministic_online_submission.tex`
- `manuscript/mej_deterministic_online_submission.pdf`
- `manuscript_audits/mej_deterministic_online_numeric_audit.md`

The versioned Zenodo archive should additionally contain all deterministic
primary/validation and online per-query netlists and logs. See
`DETERMINISTIC_ONLINE_REPRODUCIBILITY.md` for the complete release checklist.

The GF180MCU PDK checkout is not redistributed. The manuscript cites the
official repositories and reports the exact local PDK commit and model-file
provenance used for the simulations.
