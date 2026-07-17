# SKY130 Cross-PDK Protocol Replication

This experiment evaluates whether the stopping rule fixed on GF180MCU data
transfers as a protocol to a second open PDK without threshold retuning. Models
are retrained on SKY130 data; this is not a zero-shot model-transfer claim.

## Fixed PDK inputs

- ngspice 46
- SKY130 primitive repository commit
  `403964dc7f9cca5ec1a8cc7b4f2a6f532b781676`
- SKY130 high-density standard-cell repository commit
  `9cb2d7cb8ed4619094263614039a61b6b2d22a88`
- Global and mismatch statistical switches set to zero for deterministic corner
  simulation
- Official pre-layout SPICE cells from eight combinational families at drive
  strengths 1 and 4

The repositories are not redistributed. Install only the required paths with:

```bash
bash tools/install_sky130_minimal.sh sky130-pdk
export SKY130_PDK_ROOT="$PWD/sky130-pdk"
```

## Commands

Generate the two independent 576-row support datasets:

```bash
python experiments/generate_sky130_library_spice_datasets.py \
  --dataset-name primary --seed 20260718
python experiments/generate_sky130_library_spice_datasets.py \
  --dataset-name validation --seed 20260819
```

Run the 5-seed by 3-corner external replication with the GF180MCU-locked rule:

```bash
python experiments/sky130_cross_pdk_protocol_replication.py
python experiments/audit_sky130_cross_pdk_replication.py
python experiments/plot_cross_pdk_replication.py
```

## Locked decision rule

The implementation reads the previously saved GF180MCU rule and asserts these
unchanged values before any SKY130 outcome is evaluated:

- minimum budget: 64 calls
- prequential normalized MAE limit: 0.25
- successive prediction-change limit: 0.05
- coverage-ratio limit: 0.50
- two consecutive eligible batches

## Expected audit result

The audit must report `PASS`, 1,440/1,440 successful online calls, and 15/15
locked-rule outcomes within a delay-R2 gap of 0.02 relative to their measured
96-call references. The median stopping budget is 80 calls, and the maximum gap
is approximately 0.0146. Fixed 64- and 48-call budgets satisfy the same limit in
6/15 and 1/15 pools, respectively.

The complete two-PDK evidence package contains 10,093 successful SPICE calls.
The scope remains pre-layout exploration with one sensitized arc per family;
it is not complete Liberty characterization or sign-off validation.
