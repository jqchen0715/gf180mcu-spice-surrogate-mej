# SPICE V2 Pipeline

This directory is the starting point for the Microelectronics Journal extension dataset.

The goal is to replace the preliminary synthetic/inverter-only evidence with a verifiable multi-cell SPICE-grounded dataset. The pipeline is intentionally strict: by default it refuses to generate publication data unless a real GF180MCU/ngspice model file is available.

## Current Local Status

Verified on this machine:

- `ngspice` is installed: ngspice-46.
- `gf180mcu-pdk/.gitmodules` declares GF180MCU submodules.
- The required primitive and 7.5T standard-cell submodules have been initialized.
- The GF180MCU ngspice model file is available at `gf180mcu-pdk/libraries/gf180mcu_fd_pr/latest/models/ngspice/sm141064.ngspice`.
- The primary publication-eligible dataset is `data/dataset_v2_spice_320.csv`.
- The independent validation dataset is `data/dataset_v3_spice_480.csv`.

The current implementation uses transistor-level cell templates with GF180MCU primitive devices (`nmos_3p3` and `pmos_3p3`). It should be described as controlled transistor-level standard-cell topology characterization, not full Liberty characterization of the downloaded standard-cell CDL.

## Intended Dataset

Minimum seed dataset:

- Cells: `INV`, `NAND2`, `NOR2`, `XOR2`
- Samples: 30 per cell for pipeline validation
- Inputs:
  - `cell_type`
  - `Wn_um`
  - `Wp_Wn_ratio`
  - `Vdd`
  - `Temp`
  - `Cload_fF`
  - `slew_ps`
  - `corner`
- Outputs:
  - `tphl_ns`
  - `tplh_ns`
  - `delay_avg_ns`
  - `power_avg_uW`

Generated seed dataset:

- `data/dataset_v2_spice_seed.csv`
- 90 rows total: 30 each for `INV`, `NAND2`, and `NOR2`
- All rows have `status=ok` and `fidelity=SPICE_GF180MCU`

Publication-scale target:

- Cells: `INV`, `NAND2`, `NOR2`, `XOR2` minimum
- 80-120 real SPICE samples per cell
- Add `AOI21`/`OAI21` if schedule allows
- Add rise/fall power and leakage if measurement setup is stable

Current manuscript seed dataset:

- `data/dataset_v2_spice_320.csv`
- 320 rows total: 80 each for `INV`, `NAND2`, `NOR2`, and `XOR2`
- All rows have `status=ok` and `fidelity=SPICE_GF180MCU`
- First baseline/transfer results are under `results/v2/`

Current validation dataset:

- `data/dataset_v3_spice_480.csv`
- 480 rows total: 120 each for `INV`, `NAND2`, `NOR2`, and `XOR2`
- Balanced corner coverage: 160 rows each for `ff`, `ss`, and `typical`
- All rows have `status=ok` and `fidelity=SPICE_GF180MCU`
- Scale-up and corner-support results are under `results/v3_robustness/` and `results/v3_scale_validation/`

## Usage

Check whether the local PDK is usable:

```bash
.venv/bin/python spice_v2/generate_spice_dataset.py --check-only
```

Generate dry-run netlists only:

```bash
.venv/bin/python spice_v2/generate_spice_dataset.py --samples-per-cell 1 --dry-run --allow-generic-debug-models
```

Generate a debug dataset with generic MOS models:

```bash
.venv/bin/python spice_v2/generate_spice_dataset.py --samples-per-cell 1 --allow-generic-debug-models --output data/dataset_v2_debug_generic.csv
```

Do not use generic debug output in the Microelectronics Journal manuscript.

Generate real GF180MCU data:

```bash
.venv/bin/python spice_v2/generate_spice_dataset.py \
  --vdd-min 1.62 \
  --vdd-max 1.98 \
  --cells INV NAND2 NOR2 XOR2 \
  --samples-per-cell 80 \
  --output data/dataset_v2_spice_320.csv
```

Generate the independent V3 validation dataset without overwriting V2 provenance files:

```bash
.venv/bin/python spice_v2/generate_spice_dataset.py \
  --vdd-min 1.62 \
  --vdd-max 1.98 \
  --cells INV NAND2 NOR2 XOR2 \
  --samples-per-cell 120 \
  --seed 20260602 \
  --sample-id-offset 20000 \
  --netlist-dir spice_v2/netlists_v3_480 \
  --log-dir spice_v2/logs_v3_480 \
  --output data/dataset_v3_spice_480.csv
```

The default voltage range is 1.62-1.98 V to match the available 1.8 V GF180MCU standard-cell characterization corners. Wider low-voltage sweeps can be added later as a separate robustness/OOD experiment.

## Submodule Setup

If the PDK submodules are missing on another machine, initialize them:

```bash
cd gf180mcu-pdk
git submodule update --init --recursive --depth 1
```

If the model files are installed elsewhere by `open_pdks`, pass their exact path using `--model-file`.

## Publication Rule

Rows may be called `SPICE` or `SPICE-grounded` only when:

1. `model_file` points to a real GF180MCU model file.
2. `ngspice` exits with code 0.
3. The ngspice log is retained in the configured log directory.
4. The CSV row records `simulator=ngspice` and `fidelity=SPICE_GF180MCU`.
