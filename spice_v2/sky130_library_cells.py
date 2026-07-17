#!/usr/bin/env python3
"""SKY130 high-density standard-cell SPICE simulation helpers."""

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
PDK_ROOT = Path(os.environ.get("SKY130_PDK_ROOT", PROJECT_ROOT / "sky130-pdk")).expanduser().resolve()
PR_ROOT = PDK_ROOT / "libraries/sky130_fd_pr/latest"
CELL_ROOT = PDK_ROOT / "libraries/sky130_fd_sc_hd/latest/cells"
CORNER_TO_LIBRARY = {"typical": "tt", "ff": "ff", "ss": "ss"}


def corner_model_files(corner: str) -> tuple[Path, Path]:
    model_corner = CORNER_TO_LIBRARY[corner]
    return (
        PR_ROOT / "cells/nfet_01v8" / f"sky130_fd_pr__nfet_01v8__{model_corner}.pm3.spice",
        PR_ROOT / "cells/pfet_01v8_hvt" / f"sky130_fd_pr__pfet_01v8_hvt__{model_corner}.pm3.spice",
    )


MISMATCH_PARAMETER_FILES = (
    PR_ROOT / "cells/nfet_01v8/sky130_fd_pr__nfet_01v8__mismatch.corner.spice",
    PR_ROOT / "cells/pfet_01v8_hvt/sky130_fd_pr__pfet_01v8_hvt__mismatch.corner.spice",
)


@dataclass(frozen=True)
class Sky130LibraryCell:
    family: str
    source_family: str
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
    def source_variant(self) -> str:
        return f"{self.source_family}_{self.drive}"

    @property
    def subckt(self) -> str:
        return f"sky130_fd_sc_hd__{self.source_variant}"

    @property
    def spice_path(self) -> Path:
        return CELL_ROOT / self.source_family / f"{self.subckt}.spice"

    @property
    def input_arc(self) -> str:
        held = ",".join(f"{pin}={value}" for pin, value in self.fixed_inputs)
        return f"{self.active_pin}_to_{self.output_pin}" + (f"__{held}" if held else "")

    @property
    def signal_inputs(self) -> tuple[str, ...]:
        supplies = {"VGND", "VNB", "VPB", "VPWR"}
        return tuple(pin for pin in self.pins if pin not in supplies and pin != self.output_pin)


CELL_ARCS: dict[str, Sky130LibraryCell] = {
    "inv": Sky130LibraryCell(
        "inv", "inv", 1, ("A", "VGND", "VNB", "VPB", "VPWR", "Y"), "A", "Y", (), True
    ),
    "nand2": Sky130LibraryCell(
        "nand2", "nand2", 1, ("A", "B", "VGND", "VNB", "VPB", "VPWR", "Y"),
        "A", "Y", (("B", 1),), True
    ),
    "nor2": Sky130LibraryCell(
        "nor2", "nor2", 1, ("A", "B", "VGND", "VNB", "VPB", "VPWR", "Y"),
        "A", "Y", (("B", 0),), True
    ),
    "xor2": Sky130LibraryCell(
        "xor2", "xor2", 1, ("A", "B", "VGND", "VNB", "VPB", "VPWR", "X"),
        "A", "X", (("B", 0),), False
    ),
    "aoi21": Sky130LibraryCell(
        "aoi21", "a21oi", 1, ("A1", "A2", "B1", "VGND", "VNB", "VPB", "VPWR", "Y"),
        "A1", "Y", (("A2", 1), ("B1", 0)), True
    ),
    "oai21": Sky130LibraryCell(
        "oai21", "o21ai", 1, ("A1", "A2", "B1", "VGND", "VNB", "VPB", "VPWR", "Y"),
        "A1", "Y", (("A2", 0), ("B1", 1)), True
    ),
    "mux2": Sky130LibraryCell(
        "mux2", "mux2", 1, ("A0", "A1", "S", "VGND", "VNB", "VPB", "VPWR", "X"),
        "A0", "X", (("A1", 0), ("S", 0)), False
    ),
    "nand3": Sky130LibraryCell(
        "nand3", "nand3", 1, ("A", "B", "C", "VGND", "VNB", "VPB", "VPWR", "Y"),
        "A", "Y", (("B", 1), ("C", 1)), True
    ),
}


def with_drive(cell: Sky130LibraryCell, drive: int) -> Sky130LibraryCell:
    return Sky130LibraryCell(
        family=cell.family,
        source_family=cell.source_family,
        drive=drive,
        pins=cell.pins,
        active_pin=cell.active_pin,
        output_pin=cell.output_pin,
        fixed_inputs=cell.fixed_inputs,
        inverting=cell.inverting,
    )


def selected_cells(drives: tuple[int, ...] = (1, 4)) -> list[Sky130LibraryCell]:
    cells = [with_drive(cell, drive) for cell in CELL_ARCS.values() for drive in drives]
    missing = [str(cell.spice_path) for cell in cells if not cell.spice_path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing SKY130 standard-cell SPICE files: {missing}")
    model_files = [path for corner in CORNER_TO_LIBRARY for path in corner_model_files(corner)]
    model_files.extend(MISMATCH_PARAMETER_FILES)
    missing_models = [str(path) for path in model_files if not path.exists()]
    if missing_models:
        raise FileNotFoundError(f"Missing SKY130 device-model files: {missing_models}")
    return cells


def _spice_number(value: str) -> float:
    suffixes = {"t": 1e12, "g": 1e9, "meg": 1e6, "k": 1e3, "m": 1e-3,
                "u": 1e-6, "n": 1e-9, "p": 1e-12, "f": 1e-15}
    match = re.fullmatch(r"([-+\deE.]+)(meg|[tgkmunpf])?", value.strip(), re.IGNORECASE)
    if not match:
        raise ValueError(f"Unsupported SPICE number: {value}")
    number = float(match.group(1))
    suffix = (match.group(2) or "").lower()
    return number * suffixes.get(suffix, 1.0)


def device_summary(cell: Sky130LibraryCell) -> dict[str, float | int]:
    transistor_count = 0
    n_width = 0.0
    p_width = 0.0
    for line in cell.spice_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or not stripped.upper().startswith("X"):
            continue
        tokens = stripped.split()
        if len(tokens) < 6:
            continue
        model = tokens[5].lower()
        width_match = re.search(r"\bw=([-+\deE.]+(?:meg|[tgkmunpf])?)", stripped, re.IGNORECASE)
        if width_match is None:
            continue
        # SKY130 generated cell SPICE expresses micrometre dimensions using
        # values such as 650000u, which evaluates to 0.65 in the model deck.
        width_um = _spice_number(width_match.group(1))
        transistor_count += 1
        if "nfet" in model:
            n_width += width_um
        elif "pfet" in model:
            p_width += width_um
    return {
        "transistor_count": transistor_count,
        "total_n_width_um": n_width,
        "total_p_width_um": p_width,
    }


def write_library_netlist(
    cell: Sky130LibraryCell,
    sample_id: int,
    corner: str,
    vdd: float,
    temp_c: float,
    slew_ns: float,
    cload_pf: float,
    netlist_dir: Path,
) -> Path:
    if corner not in CORNER_TO_LIBRARY:
        raise ValueError(f"Unsupported SKY130 corner: {corner}")
    netlist_dir.mkdir(parents=True, exist_ok=True)
    path = netlist_dir / f"{sample_id:08d}_{cell.variant}_{corner}.cir"
    active = cell.active_pin.lower()
    output = cell.output_pin.lower()
    node_map = {pin: pin.lower() for pin in cell.pins}
    node_map.update({"VGND": "0", "VNB": "0", "VPB": "vdd", "VPWR": "vdd"})
    fixed_sources = "\n".join(
        f"VFIX_{pin} {node_map[pin]} 0 {vdd if value else 0:.8g}"
        for pin, value in cell.fixed_inputs
    )
    instance_nodes = " ".join(node_map[pin] for pin in cell.pins)
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
    model_corner = CORNER_TO_LIBRARY[corner]
    n_model, p_model = corner_model_files(corner)
    n_mismatch, p_mismatch = MISMATCH_PARAMETER_FILES
    content = f"""* SKY130 cross-PDK protocol-replication testbench
* sample_id={sample_id} cell={cell.variant} source_cell={cell.subckt} corner={corner}
.title SKY130 library cell {cell.variant} {cell.input_arc}
.option scale=1.0u method=gear reltol=1e-4 abstol=1e-12 vntol=1e-6
.temp {temp_c:.8g}
.param mc_mm_switch=0 mc_pr_switch=0
.include "{n_model}"
.include "{n_mismatch}"
.include "{p_model}"
.include "{p_mismatch}"
.include "{cell.spice_path}"

VDD vdd 0 {vdd:.8g}
VIN {active} 0 PULSE(0 {vdd:.8g} 24n {slew_ns:.8g}n {slew_ns:.8g}n 70n 160n)
{fixed_sources}
XU1 {instance_nodes} {cell.subckt}
CLOAD {output} 0 {cload_pf:.8g}p

.tran 5p 340n
{measures.strip()}
.measure tran i_vdd_avg AVG i(VDD) FROM=10n TO=330n
.measure tran power_avg_uW PARAM='-{vdd:.8g}*i_vdd_avg*1e6'
.end
"""
    path.write_text(content, encoding="utf-8")
    return path


def simulate_library_point(
    cell: Sky130LibraryCell,
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
    log_path = log_dir / f"{sample_id:08d}_{cell.variant}_{corner}.log"
    started = time.perf_counter()
    proc = subprocess.run(
        ["ngspice", "-b", str(path)],
        cwd=PR_ROOT,
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
    power = measurements.get("power_avg_uw")
    delay = None
    if tphl is not None and tplh is not None and math.isfinite(tphl) and math.isfinite(tplh):
        delay = (tphl + tplh) * 0.5 * 1e9
    valid_power = power is not None and math.isfinite(power)
    status = "ok" if proc.returncode == 0 and delay is not None and valid_power else "measure_failed"
    summary = device_summary(cell)
    return {
        "sample_id": sample_id,
        "pdk": "SKY130",
        "process_node_nm": 130,
        "cell_family": cell.family.upper(),
        "cell_variant": cell.variant.upper(),
        "source_cell_variant": cell.source_variant.upper(),
        "drive_strength": cell.drive,
        "input_arc": cell.input_arc,
        "inverting": int(cell.inverting),
        "input_count": len(cell.signal_inputs),
        **summary,
        "Vdd": vdd,
        "Temp": temp_c,
        "slew_ns": slew_ns,
        "Cload_pF": cload_pf,
        "corner": corner,
        "model_corner": CORNER_TO_LIBRARY[corner],
        "tphl_ns": None if tphl is None else tphl * 1e9,
        "tplh_ns": None if tplh is None else tplh * 1e9,
        "delay_avg_ns": delay,
        "power_avg_uW": power,
        "spice_wall_time_s": wall_time,
        "status": status,
        "fidelity": "SPICE_SKY130_RELEASED_SPICE",
        "statistical_mode": "off",
        "mc_mm_switch": 0,
        "mc_pr_switch": 0,
        "released_spice_path": str(cell.spice_path.relative_to(PROJECT_ROOT)),
        "netlist_path": str(path.relative_to(PROJECT_ROOT)),
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "ngspice_returncode": proc.returncode,
    }
