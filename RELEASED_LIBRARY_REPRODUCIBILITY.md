# Released GF180MCU Library External Validation

Updated: 2026-07-17

This document covers the released-CDL external validation, validation-blind
stopping experiment, and partial Liberty compatibility check that extend the
controlled simulator-in-the-loop study.

## 1. Environment and provenance

- ngspice 46
- GF180MCU parent PDK commit
  `de3240d7529a6970437ac3344820aaae7839f215`
- primitive-library commit
  `9f992d5a9186d1f7820c58f039c484ad35b2edea`
- 7-track standard-cell-library commit
  `43beb45e4d323a76239de436db2df6732e9a689b`
- statistical controls: `sw_stat_global=0`, `sw_stat_mismatch=0`

The PDK is not redistributed. Clone the official parent repository with its
submodules, or point the scripts to an existing checkout:

```bash
export GF180MCU_PDK_ROOT=/absolute/path/to/gf180mcu-pdk
```

Generated archived netlists use `design.ngspice` and `sm141064.ngspice` as
portable include names. Run them from the primitive model directory, or
regenerate them with the scripts below.

## 2. Released cells and device adapter

`spice_v2/gf180_library_cells.py` reads official CDLs for INV, NAND2, NOR2,
XOR2, AOI21, OAI21, MUX2, and NAND3 at drive strengths 1 and 4. One sensitized
arc is defined per family. The adapter maps released CDL `nfet_05v0` and
`pfet_05v0` instances to the open ngspice `nmos_6p0` and `pmos_6p0`
subcircuits while preserving every transistor connection, width, and length.

This mapping provides a released-topology test in the open model flow. It is
not claimed to reproduce the provider's unavailable characterization deck.

## 3. Independent datasets

Generate the two 576-row datasets with distinct sampling seeds:

```bash
python experiments/generate_library_spice_datasets.py \
  --outdir results/gf180_library_external_validation \
  --dataset-name primary --seed 20260717 \
  --samples-per-variant 36 --workers 8

python experiments/generate_library_spice_datasets.py \
  --outdir results/gf180_library_external_validation \
  --dataset-name validation --seed 20260731 \
  --samples-per-variant 36 \
  --workers 8
```

Publication files:

```text
results/gf180_library_external_validation/primary/library_primary.csv
results/gf180_library_external_validation/validation/library_validation.csv
```

Each dataset contains 36 points per cell variant and 192 points per process
corner. All 1152 simulations completed successfully in the reported run.

## 4. Measured online pools

```bash
python experiments/library_online_external_validation.py \
  --seeds 0 1 2 3 4 \
  --corners typical ff ss \
  --candidate-per-variant 6 \
  --workers 8 --resume
```

The command completes 15 pools of 96 candidates, for 1440 successful fresh
SPICE calls. The variant-balanced farthest-first order adds one point per each
of 16 variants in every batch. The full 96-query pool is the measured reference
for each seed-corner pair.

## 5. Validation-blind stopping

```bash
python experiments/validate_library_online_stopping.py
```

Seeds 0--2 are used for rule development, and seeds 3--4 remain untouched for
confirmation. The locked rule uses only prequential delay error, prediction
change, and feature-space coverage. It stops at a median of 88/96 queries on
the six confirmation pools. Five runs remain within 0.02 delay R2 and all six
remain within 0.05 of their measured references.

## 6. Partial Liberty compatibility

```bash
python experiments/liberty_surface_crosscheck.py
```

The check runs nine low/mid/high slew-load points for each of 16 variants and
three matched PVT files, giving 432 fresh simulations. The reported Spearman
correlation is 0.9900 and the median absolute percentage error is 18.58%.
These results support ordering compatibility, not complete Liberty agreement.

## 7. Figure and numeric audits

```bash
python experiments/plot_official_library_validation.py
python tools/audit_deterministic_online_manuscript.py
python tools/audit_official_library_extension.py
```

The extension audit checks row counts, statistical controls, cell coverage,
online-call counts, pooled trajectories, stopping confirmation, Liberty
metrics, manuscript tokens, figure presence, and accidental absolute user
paths in CSV data.

## 8. Interpretation boundary

The external test remains same-PDK, same-simulator, and pre-layout. It covers
eight combinational families, two drive strengths, and one sensitized arc per
family. It does not provide sequential-cell coverage, every legal timing arc,
leakage and internal-power tables, timing constraints, extracted parasitics,
cross-PDK transfer, or full Liberty characterization.
