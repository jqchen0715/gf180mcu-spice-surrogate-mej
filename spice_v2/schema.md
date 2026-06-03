# Dataset V2 Schema

This schema is intended for the Microelectronics Journal extension dataset.

## Required Columns

| Column | Unit | Meaning |
|---|---:|---|
| `sample_id` | - | Unique row identifier |
| `cell_type` | - | Standard-cell topology, e.g. `INV`, `NAND2`, `NOR2`, `XOR2` |
| `input_arc` | - | Characterized input-output arc, e.g. `A1_to_Z_A2_held_0` |
| `Wn_um` | um | NMOS width used by the seed transistor-level netlist |
| `L_um` | um | MOS channel length used by the seed transistor-level netlist |
| `Wp_Wn_ratio` | - | PMOS/NMOS width ratio |
| `Vdd` | V | Supply voltage |
| `Temp` | degC | Simulator temperature |
| `Cload_fF` | fF | Output load capacitance |
| `slew_ps` | ps | Input transition time used in the PULSE source |
| `corner` | - | Intended process corner metadata |
| `tphl_ns` | ns | High-to-low propagation delay |
| `tplh_ns` | ns | Low-to-high propagation delay |
| `delay_avg_ns` | ns | Average of `tphl_ns` and `tplh_ns` |
| `power_avg_uW` | uW | Average dynamic/switching supply power over the measurement window |
| `simulator` | - | Expected to be `ngspice` |
| `ngspice_version` | - | Simulator version string |
| `model_file` | path | Included model file; required for publication rows |
| `nmos_model` | - | NMOS model card name |
| `pmos_model` | - | PMOS model card name |
| `fidelity` | - | `SPICE_GF180MCU` or `GenericDebug_NotForPublication` |
| `status` | - | `ok`, `dry_run`, `ngspice_failed`, or `measure_failed` |
| `netlist_path` | path | Generated netlist path |
| `log_path` | path | ngspice log path |

## Publication Eligibility

A row is eligible for manuscript use only if:

- `fidelity == SPICE_GF180MCU`
- `status == ok`
- `model_file` is non-empty and points to a real GF180MCU model
- `log_path` exists and contains ngspice measurements

Rows with `GenericDebug_NotForPublication` are only for pipeline testing.
