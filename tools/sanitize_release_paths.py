#!/usr/bin/env python3
"""Replace local PDK prefixes in release CSV files and generated netlists."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import re
import tempfile


LOCAL_PDK_PREFIX = re.compile(r"/(?:Users|home)/[^,\s\"']+?/gf180mcu-pdk/")
PORTABLE_PDK_PREFIX = "gf180mcu-pdk/"


def sanitize_csv(path: Path) -> bool:
    with path.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or "model_file" not in reader.fieldnames:
            return False
        rows = list(reader)
        fieldnames = reader.fieldnames

    changed = False
    for row in rows:
        value = row.get("model_file", "")
        portable = LOCAL_PDK_PREFIX.sub(PORTABLE_PDK_PREFIX, value)
        if portable != value:
            row["model_file"] = portable
            changed = True
    if not changed:
        return False

    with tempfile.NamedTemporaryFile("w", newline="", encoding="utf-8", delete=False, dir=path.parent) as target:
        writer = csv.DictWriter(target, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        temporary = Path(target.name)
    temporary.replace(path)
    return True


def sanitize_text(path: Path) -> bool:
    source = path.read_text(encoding="utf-8")
    portable = LOCAL_PDK_PREFIX.sub(PORTABLE_PDK_PREFIX, source)
    if portable == source:
        return False
    path.write_text(portable, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    changed_csv = [path for path in args.root.rglob("*.csv") if sanitize_csv(path)]
    changed_netlists = [path for path in args.root.rglob("*.cir") if sanitize_text(path)]
    print(
        f"Sanitized {len(changed_csv)} CSV files and "
        f"{len(changed_netlists)} netlists under {args.root}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
