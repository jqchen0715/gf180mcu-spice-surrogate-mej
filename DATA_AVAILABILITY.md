# Data and Code Availability

The preceding static-table reproducibility package is archived at:

```text
https://doi.org/10.5281/zenodo.20524583
```

The live GitHub repository is:

```text
https://github.com/jqchen0715/gf180mcu-spice-surrogate-mej
```

The deterministic cross-PDK simulator-in-the-loop extension is prepared in this
live repository. Before manuscript submission, create a new GitHub release and
a new Zenodo version. The resulting version DOI should replace the preceding
DOI in the final manuscript.

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
- `spice_v2/gf180_library_cells.py`
- `experiments/generate_library_spice_datasets.py`
- `experiments/library_online_external_validation.py`
- `experiments/validate_library_online_stopping.py`
- `experiments/liberty_surface_crosscheck.py`
- `results/gf180_library_external_validation/`
- `manuscript_audits/mej_official_library_extension_numeric_audit.md`
- `spice_v2/sky130_library_cells.py`
- `experiments/generate_sky130_library_spice_datasets.py`
- `experiments/sky130_cross_pdk_protocol_replication.py`
- `experiments/audit_sky130_cross_pdk_replication.py`
- `results/sky130_cross_pdk_replication/`
- `SKY130_CROSS_PDK_REPRODUCIBILITY.md`

The prepared repository copy contains the released-library netlists and logs in
addition to the structured tables. The versioned Zenodo archive should retain
these records and the controlled-stage per-query provenance. See
`DETERMINISTIC_ONLINE_REPRODUCIBILITY.md` and
`RELEASED_LIBRARY_REPRODUCIBILITY.md` and
`SKY130_CROSS_PDK_REPRODUCIBILITY.md` for the complete release checklist.

The GF180MCU and SKY130 PDK checkouts are not redistributed. The manuscript
cites the official repositories and reports exact commits and model-file
provenance. `tools/install_sky130_minimal.sh` installs the required SKY130 paths
as a sparse checkout.
