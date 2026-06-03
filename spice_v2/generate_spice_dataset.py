#!/usr/bin/env python3
"""
Generate a seed SPICE dataset for the Microelectronics Journal extension.

This script is deliberately conservative:
- real publication rows require an explicit or discoverable GF180MCU model file;
- generic MOS models are allowed only with --allow-generic-debug-models;
- every generated row records provenance and the ngspice log path.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.stats import qmc


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDK_ROOT = PROJECT_ROOT / "gf180mcu-pdk"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "dataset_v2_spice_seed.csv"
NETLIST_DIR = PROJECT_ROOT / "spice_v2" / "netlists"
LOG_DIR = PROJECT_ROOT / "spice_v2" / "logs"


MODEL_CANDIDATES = (
    "libs.tech/ngspice/sm141064.ngspice",
    "libs.tech/ngspice/design.ngspice",
    "libs.tech/ngspice/models.spice",
    "libs.tech/ngspice/models.sp",
    "libraries/gf180mcu_fd_pr/latest/models/ngspice/sm141064.ngspice",
    "libraries/gf180mcu_fd_pr/latest/models/ngspice/design.ngspice",
)


@dataclass(frozen=True)
class Sample:
    sample_id: int
    cell_type: str
    wn_um: float
    length_um: float
    wp_wn_ratio: float
    vdd: float
    temp: float
    cload_ff: float
    slew_ps: float
    corner: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a multi-cell ngspice dataset for GF180MCU standard-cell surrogate modeling."
    )
    parser.add_argument("--pdk-root", type=Path, default=DEFAULT_PDK_ROOT)
    parser.add_argument("--model-file", type=Path, default=None)
    parser.add_argument("--nmos-model", default="nmos_3p3")
    parser.add_argument("--pmos-model", default="pmos_3p3")
    parser.add_argument("--cells", nargs="+", default=["INV", "NAND2", "NOR2", "XOR2"])
    parser.add_argument("--samples-per-cell", type=int, default=30)
    parser.add_argument("--length-um", type=float, default=0.28, help="MOS channel length in micrometers.")
    parser.add_argument("--vdd-min", type=float, default=1.62, help="Minimum supply voltage in volts.")
    parser.add_argument("--vdd-max", type=float, default=1.98, help="Maximum supply voltage in volts.")
    parser.add_argument("--seed", type=int, default=20260530)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--netlist-dir",
        type=Path,
        default=NETLIST_DIR,
        help="Directory for generated netlists. Use a separate directory for supplemental datasets.",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=LOG_DIR,
        help="Directory for ngspice logs. Use a separate directory for supplemental datasets.",
    )
    parser.add_argument(
        "--sample-id-offset",
        type=int,
        default=0,
        help="Integer offset added to generated sample IDs to avoid provenance filename collisions.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Write netlists but do not run ngspice.")
    parser.add_argument("--check-only", action="store_true", help="Only validate local prerequisites.")
    parser.add_argument(
        "--allow-generic-debug-models",
        action="store_true",
        help="Use simple LEVEL=1 MOS models for pipeline debugging. Not valid for publication.",
    )
    args = parser.parse_args()
    args.output = project_root_path(args.output)
    args.netlist_dir = project_root_path(args.netlist_dir)
    args.log_dir = project_root_path(args.log_dir)
    return args


def project_root_path(path: Path) -> Path:
    expanded = path.expanduser()
    return expanded if expanded.is_absolute() else PROJECT_ROOT / expanded


def find_model_file(pdk_root: Path, explicit: Path | None) -> Path | None:
    if explicit:
        return explicit.expanduser().resolve() if explicit.exists() else explicit.expanduser().resolve()

    for rel in MODEL_CANDIDATES:
        candidate = pdk_root / rel
        if candidate.exists():
            return candidate.resolve()

    matches = []
    if pdk_root.exists():
        for pattern in ("*.ngspice", "*.spice", "*.sp", "*.lib"):
            matches.extend(pdk_root.rglob(pattern))
    return matches[0].resolve() if matches else None


def pdk_submodule_status(pdk_root: Path) -> list[str]:
    empty = []
    for rel in (
        "libraries/gf180mcu_fd_pr/latest",
        "libraries/gf180mcu_fd_sc_mcu7t5v0/latest",
    ):
        path = pdk_root / rel
        if not path.exists() or not any(path.iterdir()):
            empty.append(rel)
    return empty


def check_prerequisites(args: argparse.Namespace) -> tuple[Path | None, list[str]]:
    issues: list[str] = []
    if shutil.which("ngspice") is None:
        issues.append("ngspice was not found on PATH.")

    if not args.pdk_root.exists():
        issues.append(f"PDK root does not exist: {args.pdk_root}")

    empty_submodules = pdk_submodule_status(args.pdk_root)
    if empty_submodules:
        issues.append("Empty GF180MCU submodule directories: " + ", ".join(empty_submodules))

    model_file = find_model_file(args.pdk_root, args.model_file)
    if model_file is None or not model_file.exists():
        issues.append("No GF180MCU ngspice model file was found. Pass --model-file or initialize submodules.")

    return model_file, issues


def lhs_samples(
    cells: list[str],
    samples_per_cell: int,
    seed: int,
    length_um: float,
    vdd_range: tuple[float, float],
) -> list[Sample]:
    rows: list[Sample] = []
    sample_id = 0

    ranges = {
        "wn_um": (0.5, 5.0),
        "wp_wn_ratio": (1.5, 3.0),
        "vdd": vdd_range,
        "temp": (-20.0, 100.0),
        "cload_ff": (1.0, 100.0),
        "slew_ps": (10.0, 500.0),
    }
    corners = ["typical", "ss", "ff"]

    for cell_idx, cell in enumerate(cells):
        sampler = qmc.LatinHypercube(d=6, seed=seed + cell_idx)
        unit = sampler.random(n=samples_per_cell)
        scaled = qmc.scale(unit, [v[0] for v in ranges.values()], [v[1] for v in ranges.values()])

        for i, values in enumerate(scaled):
            corner = corners[i % len(corners)]
            rows.append(
                Sample(
                    sample_id=sample_id,
                    cell_type=cell.upper(),
                    wn_um=float(values[0]),
                    length_um=length_um,
                    wp_wn_ratio=float(values[1]),
                    vdd=float(values[2]),
                    temp=float(values[3]),
                    cload_ff=float(values[4]),
                    slew_ps=float(values[5]),
                    corner=corner,
                )
            )
            sample_id += 1

    return rows


def offset_sample_ids(samples: list[Sample], offset: int) -> list[Sample]:
    if offset == 0:
        return samples
    return [
        Sample(
            sample_id=sample.sample_id + offset,
            cell_type=sample.cell_type,
            wn_um=sample.wn_um,
            length_um=sample.length_um,
            wp_wn_ratio=sample.wp_wn_ratio,
            vdd=sample.vdd,
            temp=sample.temp,
            cload_ff=sample.cload_ff,
            slew_ps=sample.slew_ps,
            corner=sample.corner,
        )
        for sample in samples
    ]


def project_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def mos_models_block(
    model_file: Path | None,
    use_generic: bool,
    nmos_model: str,
    pmos_model: str,
    corner: str,
) -> str:
    if use_generic:
        return f"""
* DEBUG ONLY: generic MOS models, not GF180MCU publication data.
.model {nmos_model} nmos level=1 vto=0.45 kp=180u gamma=0.45 lambda=0.05 phi=0.7
.model {pmos_model} pmos level=1 vto=-0.45 kp=70u gamma=0.45 lambda=0.05 phi=0.7
"""
    if model_file is None:
        raise ValueError("A real model file is required unless --allow-generic-debug-models is used.")
    design_file = model_file.parent / "design.ngspice"
    design_include = f'.include "{design_file}"\n' if design_file.exists() else ""
    return f'{design_include}.lib "{model_file}" {corner}\n'


def cell_devices(sample: Sample, nmos_model: str, pmos_model: str, use_subckt_models: bool) -> str:
    wn = sample.wn_um
    wp = sample.wn_um * sample.wp_wn_ratio
    length = sample.length_um
    cell = sample.cell_type.upper()
    nprefix = "Xn" if use_subckt_models else "Mn"
    pprefix = "Xp" if use_subckt_models else "Mp"

    if cell == "INV":
        return f"""
{nprefix}1 out in 0 0 {nmos_model} W={wn:.6g}u L={length}u
{pprefix}1 out in vdd vdd {pmos_model} W={wp:.6g}u L={length}u
"""

    if cell == "NAND2":
        return f"""
{nprefix}1 out in nmid 0 {nmos_model} W={wn:.6g}u L={length}u
{nprefix}2 nmid in 0 0 {nmos_model} W={wn:.6g}u L={length}u
{pprefix}1 out in vdd vdd {pmos_model} W={wp:.6g}u L={length}u
{pprefix}2 out in vdd vdd {pmos_model} W={wp:.6g}u L={length}u
"""

    if cell == "NOR2":
        return f"""
{nprefix}1 out in 0 0 {nmos_model} W={wn:.6g}u L={length}u
{nprefix}2 out in 0 0 {nmos_model} W={wn:.6g}u L={length}u
{pprefix}1 pmid in vdd vdd {pmos_model} W={wp:.6g}u L={length}u
{pprefix}2 out in pmid vdd {pmos_model} W={wp:.6g}u L={length}u
"""

    if cell == "XOR2":
        tg_n = wn * 1.25
        tg_p = wp * 1.25
        return f"""
        * XOR2 A1->Z arc with A2 held at VDD:
        * out = in xor b, b = VDD. Internal inverters create abar and bbar.
{nprefix}a_inv abar in 0 0 {nmos_model} W={wn:.6g}u L={length}u
{pprefix}a_inv abar in vdd vdd {pmos_model} W={wp:.6g}u L={length}u
{nprefix}b_inv bbar b 0 0 {nmos_model} W={wn:.6g}u L={length}u
{pprefix}b_inv bbar b vdd vdd {pmos_model} W={wp:.6g}u L={length}u
{nprefix}pass_a out bbar in 0 {nmos_model} W={tg_n:.6g}u L={length}u
{pprefix}pass_a out b in vdd {pmos_model} W={tg_p:.6g}u L={length}u
{nprefix}pass_abar out b abar 0 {nmos_model} W={tg_n:.6g}u L={length}u
{pprefix}pass_abar out bbar abar vdd {pmos_model} W={tg_p:.6g}u L={length}u
"""

    raise ValueError(f"Unsupported cell type for seed pipeline: {cell}")


def write_netlist(
    sample: Sample,
    model_file: Path | None,
    args: argparse.Namespace,
) -> Path:
    args.netlist_dir.mkdir(parents=True, exist_ok=True)
    netlist_path = args.netlist_dir / f"{sample.sample_id:05d}_{sample.cell_type}.cir"

    trise = sample.slew_ps * 1e-12
    tfall = sample.slew_ps * 1e-12
    cload = sample.cload_ff * 1e-15
    pulse_delay = 2e-9
    pulse_width = 20e-9
    pulse_period = 40e-9
    sim_stop = 120e-9
    power_from = 5e-9
    power_to = 110e-9
    fixed_inputs = f"Vb b 0 {sample.vdd:.6g}\n" if sample.cell_type.upper() == "XOR2" else ""

    content = f"""* Auto-generated by spice_v2/generate_spice_dataset.py
* sample_id={sample.sample_id} cell={sample.cell_type} corner={sample.corner}
.title {sample.cell_type} seed characterization sample {sample.sample_id}
.option method=gear reltol=1e-4 abstol=1e-12 vntol=1e-6
.temp {sample.temp:.6g}
{mos_models_block(model_file, args.allow_generic_debug_models, args.nmos_model, args.pmos_model, sample.corner)}
VDD vdd 0 {sample.vdd:.6g}
Vin in 0 PULSE(0 {sample.vdd:.6g} {pulse_delay:.6e} {trise:.6e} {tfall:.6e} {pulse_width:.6e} {pulse_period:.6e})
{fixed_inputs}{cell_devices(sample, args.nmos_model, args.pmos_model, not args.allow_generic_debug_models)}
Cload out 0 {cload:.6e}

.tran 2p {sim_stop:.6e}
.measure tran tphl TRIG v(in) VAL={sample.vdd / 2:.6g} RISE=1 TARG v(out) VAL={sample.vdd / 2:.6g} FALL=1
.measure tran tplh TRIG v(in) VAL={sample.vdd / 2:.6g} FALL=1 TARG v(out) VAL={sample.vdd / 2:.6g} RISE=1
.measure tran i_vdd_avg AVG i(VDD) FROM={power_from:.6e} TO={power_to:.6e}
.measure tran power_avg_uW PARAM='-{sample.vdd:.6g}*i_vdd_avg*1e6'
.end
"""

    netlist_path.write_text(content, encoding="utf-8")
    return netlist_path


MEASURE_RE = re.compile(r"^\s*([a-zA-Z_][\w]*)\s*=\s*([-+]?\d+(?:\.\d*)?(?:[eE][-+]?\d+)?)")


def parse_measurements(text: str) -> dict[str, float]:
    measurements: dict[str, float] = {}
    for line in text.splitlines():
        match = MEASURE_RE.match(line)
        if not match:
            continue
        key, value = match.groups()
        measurements[key.lower()] = float(value)
    return measurements


def run_ngspice(
    netlist_path: Path,
    sample: Sample,
    model_file: Path | None,
    log_dir: Path,
) -> tuple[int, dict[str, float], Path]:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{sample.sample_id:05d}_{sample.cell_type}.log"
    run_cwd = model_file.parent if model_file is not None else PROJECT_ROOT
    proc = subprocess.run(
        ["ngspice", "-b", str(netlist_path)],
        cwd=run_cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    log_path.write_text(proc.stdout, encoding="utf-8", errors="replace")
    return proc.returncode, parse_measurements(proc.stdout), log_path


def result_row(
    sample: Sample,
    netlist_path: Path,
    log_path: Path | None,
    model_file: Path | None,
    measurements: dict[str, float],
    returncode: int | None,
    args: argparse.Namespace,
) -> dict[str, object]:
    tphl = measurements.get("tphl")
    tplh = measurements.get("tplh")
    delay_avg = None
    if tphl is not None and tplh is not None and math.isfinite(tphl) and math.isfinite(tplh):
        delay_avg = (tphl + tplh) / 2 * 1e9

    fidelity = "GenericDebug_NotForPublication" if args.allow_generic_debug_models else "SPICE_GF180MCU"
    status = "dry_run" if args.dry_run else "ok"
    if returncode not in (None, 0):
        status = "ngspice_failed"
    if not args.dry_run and delay_avg is None:
        status = "measure_failed"

    return {
        "sample_id": sample.sample_id,
        "cell_type": sample.cell_type,
        "input_arc": input_arc(sample.cell_type),
        "Wn_um": sample.wn_um,
        "L_um": sample.length_um,
        "Wp_Wn_ratio": sample.wp_wn_ratio,
        "Vdd": sample.vdd,
        "Temp": sample.temp,
        "Cload_fF": sample.cload_ff,
        "slew_ps": sample.slew_ps,
        "corner": sample.corner,
        "tphl_ns": None if tphl is None else tphl * 1e9,
        "tplh_ns": None if tplh is None else tplh * 1e9,
        "delay_avg_ns": delay_avg,
        "power_avg_uW": measurements.get("power_avg_uw"),
        "simulator": "ngspice",
        "ngspice_version": ngspice_version(),
        "model_file": "" if model_file is None else str(model_file),
        "nmos_model": args.nmos_model,
        "pmos_model": args.pmos_model,
        "fidelity": fidelity,
        "status": status,
        "netlist_path": project_path(netlist_path),
        "log_path": "" if log_path is None else project_path(log_path),
    }


def input_arc(cell_type: str) -> str:
    cell = cell_type.upper()
    if cell == "INV":
        return "I_to_Z"
    if cell in {"NAND2", "NOR2"}:
        return "A1_A2_tied_to_Z"
    if cell == "XOR2":
        return "A1_to_Z_A2_held_1"
    return "unknown"


def ngspice_version() -> str:
    try:
        proc = subprocess.run(["ngspice", "-v"], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        first = next((line.strip() for line in proc.stdout.splitlines() if "ngspice-" in line), "")
        return first.replace("**", "").strip()
    except Exception:
        return "unknown"


def write_csv(rows: list[dict[str, object]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with output.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_prereq_report(model_file: Path | None, issues: list[str], args: argparse.Namespace) -> None:
    print("SPICE V2 prerequisite check")
    print("=" * 72)
    print(f"ngspice: {shutil.which('ngspice') or 'NOT FOUND'}")
    print(f"pdk_root: {args.pdk_root}")
    print(f"model_file: {model_file if model_file else 'NOT FOUND'}")
    print()
    if issues:
        print("Issues:")
        for issue in issues:
            print(f"  - {issue}")
        print()
        print("Suggested fix:")
        print("  cd gf180mcu-pdk")
        print("  git submodule update --init --recursive --depth 1")
        print("  # or pass --model-file /path/to/gf180mcu/ngspice/model.spice")
    else:
        print("All prerequisites are available for real GF180MCU ngspice generation.")


def main() -> int:
    args = parse_args()
    model_file, issues = check_prerequisites(args)

    if args.check_only:
        print_prereq_report(model_file, issues, args)
        return 1 if issues else 0

    blocking_issues = [issue for issue in issues if not issue.startswith("Empty GF180MCU submodule")]
    if (model_file is None or not model_file.exists()) and not args.allow_generic_debug_models:
        print_prereq_report(model_file, issues, args)
        print()
        print("Refusing to generate publication data without a real GF180MCU model file.")
        return 2

    if args.allow_generic_debug_models:
        model_file = None
        print("WARNING: using generic debug MOS models. Output is not valid publication data.")
    elif blocking_issues:
        print_prereq_report(model_file, issues, args)
        return 2

    samples = lhs_samples(
        [c.upper() for c in args.cells],
        args.samples_per_cell,
        args.seed,
        args.length_um,
        (args.vdd_min, args.vdd_max),
    )
    samples = offset_sample_ids(samples, args.sample_id_offset)
    rows: list[dict[str, object]] = []
    failures = 0

    for sample in samples:
        netlist_path = write_netlist(sample, model_file, args)
        if args.dry_run:
            rows.append(result_row(sample, netlist_path, None, model_file, {}, None, args))
            continue

        returncode, measurements, log_path = run_ngspice(netlist_path, sample, model_file, args.log_dir)
        row = result_row(sample, netlist_path, log_path, model_file, measurements, returncode, args)
        rows.append(row)
        if row["status"] != "ok":
            failures += 1

    write_csv(rows, args.output)
    print(f"Wrote {len(rows)} rows to {args.output}")
    if failures:
        print(f"WARNING: {failures} rows failed. Inspect spice_v2/logs/.")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
