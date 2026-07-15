#!/usr/bin/env python3
"""Replace local model-file prefixes in release CSV files with a portable path."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import tempfile


LOCAL_PREFIXES = (
    "/Users/jiaqing/new_paper/gf180mcu-pdk/",
    str(Path.home() / "new_paper" / "gf180mcu-pdk") + "/",
)


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
        for prefix in LOCAL_PREFIXES:
            if value.startswith(prefix):
                row["model_file"] = "gf180mcu-pdk/" + value[len(prefix):]
                changed = True
                break
    if not changed:
        return False

    with tempfile.NamedTemporaryFile("w", newline="", encoding="utf-8", delete=False, dir=path.parent) as target:
        writer = csv.DictWriter(target, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        temporary = Path(target.name)
    temporary.replace(path)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    changed = [path for path in args.root.rglob("*.csv") if sanitize_csv(path)]
    print(f"Sanitized {len(changed)} CSV files under {args.root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
