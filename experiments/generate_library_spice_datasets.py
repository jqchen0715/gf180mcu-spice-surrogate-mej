#!/usr/bin/env python3
"""Generate independent SPICE datasets from released GF180MCU cell CDLs."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from scipy.stats import qmc


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from spice_v2.gf180_library_cells import selected_cells, simulate_library_point  # noqa: E402


DEFAULT_OUTDIR = PROJECT_ROOT / "results" / "gf180_library_external_validation"
CORNER_SEQUENCE = ("typical", "ff", "ss")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--samples-per-variant", type=int, default=36)
    parser.add_argument("--seed", type=int, default=20260717)
    parser.add_argument("--dataset-name", default="primary")
    parser.add_argument("--drives", nargs="*", type=int, default=[1, 4])
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--smoke-test", action="store_true")
    args = parser.parse_args()
    args.outdir = args.outdir.expanduser().resolve()
    return args


def design_points(n: int, seed: int) -> np.ndarray:
    sampler = qmc.LatinHypercube(d=4, seed=seed)
    unit = sampler.random(n=n)
    return qmc.scale(unit, [1.62, -40.0, 0.02, 0.001], [1.98, 125.0, 12.0, 0.2059])


def main() -> int:
    args = parse_args()
    cells = selected_cells(tuple(args.drives))
    samples_per_variant = 1 if args.smoke_test else args.samples_per_variant
    output_root = args.outdir / ("smoke" if args.smoke_test else args.dataset_name)
    netlist_dir = output_root / "netlists"
    log_dir = output_root / "logs"
    tasks = []
    sample_id = 8_000_000 if args.dataset_name == "primary" else 9_000_000
    for cell_index, cell in enumerate(cells):
        points = design_points(samples_per_variant, args.seed + cell_index * 101)
        for point_index, (vdd, temp, slew, cload) in enumerate(points):
            if args.smoke_test:
                vdd, temp, slew, cload = 1.8, 25.0, 0.1027, 0.01686
            corner = CORNER_SEQUENCE[point_index % len(CORNER_SEQUENCE)]
            tasks.append((cell, sample_id, corner, vdd, temp, slew, cload))
            sample_id += 1

    rows = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {
            executor.submit(
                simulate_library_point,
                cell,
                sid,
                corner,
                float(vdd),
                float(temp),
                float(slew),
                float(cload),
                netlist_dir,
                log_dir,
            ): (cell.variant, corner)
            for cell, sid, corner, vdd, temp, slew, cload in tasks
        }
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            print(f"{row['cell_variant']} {row['corner']} {row['status']} delay={row['delay_avg_ns']}", flush=True)

    frame = pd.DataFrame(rows).sort_values("sample_id").reset_index(drop=True)
    output_root.mkdir(parents=True, exist_ok=True)
    output = output_root / f"library_{args.dataset_name}.csv"
    frame.to_csv(output, index=False)
    failures = frame[frame["status"] != "ok"]
    print(f"Wrote {len(frame)} rows to {output}")
    print(f"Successful rows: {len(frame) - len(failures)}; failures: {len(failures)}")
    return 0 if failures.empty else 3


if __name__ == "__main__":
    raise SystemExit(main())
