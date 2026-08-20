#!/usr/bin/env python3
"""Hash VCD trace content while ignoring the generator's wall-clock date."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def normalized_vcd(data: str) -> str:
    """Return VCD text without its non-deterministic ``$date`` block."""

    normalized: list[str] = []
    skipping_date = False
    for line in data.splitlines(keepends=True):
        if not skipping_date and line.strip() == "$date":
            skipping_date = True
            continue
        if skipping_date:
            if line.strip() == "$end":
                skipping_date = False
            continue
        normalized.append(line)
    if skipping_date:
        raise ValueError("unterminated $date block")
    return "".join(normalized)


def trace_sha256(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    payload = normalized_vcd(text).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    for path in args.paths:
        print(f"{trace_sha256(path)}  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
