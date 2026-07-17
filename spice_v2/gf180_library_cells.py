#!/usr/bin/env python3
"""GF180MCU 7-track standard-cell CDL simulation helpers.

The released CDL uses foundry-facing ``nfet_05v0``/``pfet_05v0`` model names.
The open ngspice deck exposes the corresponding devices as the
``nmos_6p0``/``pmos_6p0`` subcircuits, so the small adapter below converts
only device instance prefixes and model names while preserving every released
transistor dimension and connection.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any

from spice_v2.generate_spice_dataset import parse_measurements


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PDK_ROOT = Path(os.environ.get("GF180MCU_PDK_ROOT", PROJECT_ROOT / "gf180mcu-pdk")).expanduser().resolve()
PR_MODEL = PDK_ROOT / "libraries/gf180mcu_fd_pr/latest/models/ngspice/sm141064.ngspice"
DESIGN_MODEL = PR_MODEL.parent / "design.ngspice"
CELL_ROOT = PDK_ROOT / "libraries/gf180mcu_fd_sc_mcu7t5v0/latest/cells"


@dataclass(frozen=True)
class LibraryCell:
    family: str
    drive: int
    pins: tuple[str, ...]
    active_pin: str
    output_pin: str
    fixed_inputs: tuple[tuple[str, int], ...]
    inverting: bool

    @property
    def variant(self) -> str:
        return f"{self.family}_{self.drive}"

    @property
    def subckt(self) -> str:
        return f"gf180mcu_fd_sc_mcu7t5v0__{self.variant}"

    @property
    def cdl_path(self) -> Path:
        return CELL_ROOT / self.family / f"{self.subckt}.cdl"

    @property
    def input_arc(self) -> str:
        held = ",".join(f"{pin}={value}" for pin, value in self.fixed_inputs)
        return f"{self.active_pin}_to_{self.output_pin}" + (f"__{held}" if held else "")


CELL_ARCS: dict[str, LibraryCell] = {
    "inv": LibraryCell("inv", 1, ("I", "ZN"), "I", "ZN", (), True),
    "nand2": LibraryCell("nand2", 1, ("A1", "A2", "ZN"), "A1", "ZN", (("A2", 1),), True),
    "nor2": LibraryCell("nor2", 1, ("A1", "A2", "ZN"), "A1", "ZN", (("A2", 0),), True),
    "xor2": LibraryCell("xor2", 1, ("A1", "A2", "Z"), "A1", "Z", (("A2", 0),), False),
    "aoi21": LibraryCell(
        "aoi21", 1, ("A1", "A2", "B", "ZN"), "A1", "ZN", (("A2", 1), ("B", 0)), True
    ),
    "oai21": LibraryCell(
        "oai21", 1, ("A1", "A2", "B", "ZN"), "A1", "ZN", (("A2", 0), ("B", 1)), True
    ),
    "mux2": LibraryCell(
        "mux2", 1, ("I0", "I1", "S", "Z"), "I0", "Z", (("I1", 0), ("S", 0)), False
    ),
    "nand3": LibraryCell(
        "nand3", 1, ("A1", "A2", "A3", "ZN"), "A1", "ZN", (("A2", 1), ("A3", 1)), True
    ),
}


def with_drive(cell: LibraryCell, drive: int) -> LibraryCell:
    return LibraryCell(
        family=cell.family,
        drive=drive,
        pins=cell.pins,
        active_pin=cell.active_pin,
        output_pin=cell.output_pin,
        fixed_inputs=cell.fixed_inputs,
        inverting=cell.inverting,
    )


def selected_cells(drives: tuple[int, ...] = (1, 4)) -> list[LibraryCell]:
    return [with_drive(cell, drive) for cell in CELL_ARCS.values() for drive in drives]


def cdl_device_summary(cell: LibraryCell) -> dict[str, float | int]:
    text = cell.cdl_path.read_text(encoding="utf-8")
    transistor_count = 0
    n_width = 0.0
    p_width = 0.0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped[0].upper() != "M":
            continue
        tokens = stripped.split()
        if len(tokens) < 6:
            continue
        model = tokens[5].lower()
        width_match = re.search(r"\bW=([-+\deE.]+)", stripped, re.IGNORECASE)
        width = float(width_match.group(1)) * 1e6 if width_match else 0.0
        transistor_count += 1
        if model == "nfet_05v0":
            n_width += width
        elif model == "pfet_05v0":
            p_width += width
    return {
        "transistor_count": transistor_count,
        "total_n_width_um": n_width,
        "total_p_width_um": p_width,
    }


def ngspice_cdl(cell: LibraryCell) -> str:
    """Return a device-name-adapted copy of one released CDL subcircuit."""
    lines: list[str] = []
    for line in cell.cdl_path.read_text(encoding="utf-8").splitlines():
        stripped = line.lstrip()
        if not stripped or stripped[0].upper() != "M":
            lines.append(line)
            continue
        indent = line[: len(line) - len(stripped)]
        tokens = stripped.split()
        if len(tokens) < 6:
            raise ValueError(f"Malformed CDL device line in {cell.cdl_path}: {line}")
        tokens[0] = "X" + tokens[0][1:]
        model = tokens[5].lower()
        if model == "nfet_05v0":
            tokens[5] = "nmos_6p0"
        elif model == "pfet_05v0":
            tokens[5] = "pmos_6p0"
        else:
            raise ValueError(f"Unsupported released CDL model {tokens[5]} in {cell.cdl_path}")
        lines.append(indent + " ".join(tokens))
    return "\n".join(lines) + "\n"


def write_library_netlist(
    cell: LibraryCell,
    sample_id: int,
    corner: str,
    vdd: float,
    temp_c: float,
    slew_ns: float,
    cload_pf: float,
    netlist_dir: Path,
) -> Path:
    netlist_dir.mkdir(parents=True, exist_ok=True)
    path = netlist_dir / f"{sample_id:07d}_{cell.variant}_{corner}.cir"
    active = cell.active_pin.lower()
    output = cell.output_pin.lower()
    nodes = {pin: pin.lower() for pin in cell.pins}
    fixed_sources = "\n".join(
        f"VFIX_{pin} {nodes[pin]} 0 {vdd if value else 0:.8g}"
        for pin, value in cell.fixed_inputs
    )
    instance_nodes = " ".join(nodes[pin] for pin in cell.pins)
    if cell.inverting:
        measures = f"""
.measure tran tphl TRIG v({active}) VAL={vdd / 2:.8g} RISE=1 TARG v({output}) VAL={vdd / 2:.8g} FALL=1
.measure tran tplh TRIG v({active}) VAL={vdd / 2:.8g} FALL=1 TARG v({output}) VAL={vdd / 2:.8g} RISE=1
"""
    else:
        measures = f"""
.measure tran tplh TRIG v({active}) VAL={vdd / 2:.8g} RISE=1 TARG v({output}) VAL={vdd / 2:.8g} RISE=1
.measure tran tphl TRIG v({active}) VAL={vdd / 2:.8g} FALL=1 TARG v({output}) VAL={vdd / 2:.8g} FALL=1
"""
    pulse_delay_ns = 24.0
    pulse_width_ns = 70.0
    pulse_period_ns = 160.0
    sim_stop_ns = 340.0
    content = f"""* Released GF180MCU 7-track CDL external-validation testbench
* sample_id={sample_id} cell={cell.variant} arc={cell.input_arc} corner={corner}
.title GF180MCU library cell {cell.variant} {cell.input_arc}
.option method=gear reltol=1e-4 abstol=1e-12 vntol=1e-6
.temp {temp_c:.8g}
.include "{DESIGN_MODEL.name}"
.param sw_stat_global=0 sw_stat_mismatch=0
.lib "{PR_MODEL.name}" {corner}

{ngspice_cdl(cell)}
VDD vdd 0 {vdd:.8g}
VIN {active} 0 PULSE(0 {vdd:.8g} {pulse_delay_ns}n {slew_ns:.8g}n {slew_ns:.8g}n {pulse_width_ns}n {pulse_period_ns}n)
{fixed_sources}
XU1 {instance_nodes} vdd vdd 0 0 {cell.subckt}
CLOAD {output} 0 {cload_pf:.8g}p

.tran 5p {sim_stop_ns}n
{measures.strip()}
.measure tran i_vdd_avg AVG i(VDD) FROM=10n TO=330n
.measure tran power_avg_uW PARAM='-{vdd:.8g}*i_vdd_avg*1e6'
.end
"""
    path.write_text(content, encoding="utf-8")
    return path


def simulate_library_point(
    cell: LibraryCell,
    sample_id: int,
    corner: str,
    vdd: float,
    temp_c: float,
    slew_ns: float,
    cload_pf: float,
    netlist_dir: Path,
    log_dir: Path,
) -> dict[str, Any]:
    path = write_library_netlist(cell, sample_id, corner, vdd, temp_c, slew_ns, cload_pf, netlist_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{sample_id:07d}_{cell.variant}_{corner}.log"
    started = time.perf_counter()
    proc = subprocess.run(
        ["ngspice", "-b", str(path)],
        cwd=PR_MODEL.parent,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    wall_time = time.perf_counter() - started
    log_path.write_text(proc.stdout, encoding="utf-8", errors="replace")
    measurements = parse_measurements(proc.stdout)
    tphl = measurements.get("tphl")
    tplh = measurements.get("tplh")
    delay = None
    if tphl is not None and tplh is not None and math.isfinite(tphl) and math.isfinite(tplh):
        delay = (tphl + tplh) * 0.5 * 1e9
    status = "ok" if proc.returncode == 0 and delay is not None else "measure_failed"
    summary = cdl_device_summary(cell)
    return {
        "sample_id": sample_id,
        "cell_family": cell.family.upper(),
        "cell_variant": cell.variant.upper(),
        "drive_strength": cell.drive,
        "input_arc": cell.input_arc,
        "inverting": int(cell.inverting),
        "input_count": len(cell.pins) - 1,
        **summary,
        "Vdd": vdd,
        "Temp": temp_c,
        "slew_ns": slew_ns,
        "Cload_pF": cload_pf,
        "corner": corner,
        "tphl_ns": None if tphl is None else tphl * 1e9,
        "tplh_ns": None if tplh is None else tplh * 1e9,
        "delay_avg_ns": delay,
        "power_avg_uW": measurements.get("power_avg_uw"),
        "spice_wall_time_s": wall_time,
        "status": status,
        "fidelity": "SPICE_GF180MCU_RELEASED_CDL",
        "statistical_mode": "off",
        "sw_stat_global": 0,
        "sw_stat_mismatch": 0,
        "released_cdl_path": str(cell.cdl_path.relative_to(PROJECT_ROOT)),
        "netlist_path": str(path.relative_to(PROJECT_ROOT)),
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "ngspice_returncode": proc.returncode,
    }
