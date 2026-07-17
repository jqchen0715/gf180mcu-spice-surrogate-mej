# v0.5.0: Cross-PDK simulator-in-the-loop validation

This release archives the complete reproducibility package for the expanded
Microelectronics Journal study.

## Main additions

- deterministic GF180MCU primary and independent validation datasets;
- validation-blind simulator-in-the-loop acquisition with measured 96-call
  references and retained per-query netlists and ngspice logs;
- released GF180MCU standard-cell validation across eight combinational
  families and two drive strengths;
- a stopping rule locked on nine GF180MCU development pools and evaluated on
  six untouched GF180MCU confirmation pools;
- external SKY130 replication over 15 completed pools without threshold
  retuning;
- a 432-point partial GF180MCU Liberty compatibility check;
- the publication manuscript, figures, numeric audits, exact PDK commits, and
  sparse SKY130 installation protocol.

## Scope boundary

The package supports pre-layout standard-cell exploration with PDK-specific
model retraining. It does not claim zero-shot model transfer, layout-extracted
sign-off, all timing arcs, sequential-cell characterization, or complete
Liberty generation.
