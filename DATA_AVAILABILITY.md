# Data and Code Availability

The complete cross-PDK reproducibility package is archived at:

```text
https://doi.org/10.5281/zenodo.21425560
```

The live GitHub repository is:

```text
https://github.com/jqchen0715/gf180mcu-spice-surrogate-mej
```

Release `v0.6.0` contains the deterministic cross-PDK simulator-in-the-loop
extension together with the prospective seed-5 confirmation, precommit and
decision artifacts, exact intervals, ablations, tail metrics, cost ledger, and
revision-risk audits. DOI `10.5281/zenodo.21425560` identifies this immutable
release. DOI `10.5281/zenodo.21415175` identifies the preceding `v0.5.0`
completed-pool package, and DOI `10.5281/zenodo.20524583` remains the permanent
record of the earlier `v0.1.0` package.

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
- `experiments/prospective_locked_rule_confirmation.py`
- `experiments/revision_risk_audit.py`
- `tools/audit_revision_manuscript.py`
- `results/prospective_locked_confirmation/`
- `results/revision_risk_audit/`
- `PROSPECTIVE_CONFIRMATION_REPRODUCIBILITY.md`

The release contains the controlled-stage and released-library netlists and
logs in addition to the structured tables. The versioned Zenodo archive retains
these records as per-query provenance. See
`DETERMINISTIC_ONLINE_REPRODUCIBILITY.md` and
`RELEASED_LIBRARY_REPRODUCIBILITY.md` and
`SKY130_CROSS_PDK_REPRODUCIBILITY.md` for the complete release checklist.

The GF180MCU and SKY130 PDK checkouts are not redistributed. The manuscript
cites the official repositories and reports exact commits and model-file
provenance. `tools/install_sky130_minimal.sh` installs the required SKY130 paths
as a sparse checkout.
