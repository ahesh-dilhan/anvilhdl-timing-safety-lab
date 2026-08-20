#!/usr/bin/env python3
"""Collect comparable Quartus metrics from one or more variant build trees."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Iterable


CSV_FIELDS = (
    "variant",
    "flow_status",
    "quartus_version",
    "family",
    "device",
    "clock_period_ns",
    "logic_elements",
    "combinational_functions",
    "dedicated_logic_registers",
    "total_registers",
    "memory_bits",
    "multipliers_9bit",
    "worst_setup_slack_ns",
    "fmax_mhz",
    "restricted_fmax_mhz",
    "flow_elapsed_s",
)


def _first_report(output_dir: Path, suffix: str) -> Path:
    matches = sorted(output_dir.glob(f"*.{suffix}"))
    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one *.{suffix} in {output_dir}, found {len(matches)}"
        )
    return matches[0]


def _summary_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in text.splitlines():
        if ":" not in raw_line:
            continue
        key, value = raw_line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def _leading_integer(value: str) -> int:
    match = re.search(r"[\d,]+", value)
    if match is None:
        raise ValueError(f"could not find an integer in {value!r}")
    return int(match.group(0).replace(",", ""))


def _elapsed_seconds(flow_text: str) -> int | None:
    match = re.search(
        r"^;\s*Total\s*;\s*(\d{2}):(\d{2}):(\d{2})\s*;",
        flow_text,
        flags=re.MULTILINE,
    )
    if match is None:
        return None
    hours, minutes, seconds = (int(part) for part in match.groups())
    return hours * 3600 + minutes * 60 + seconds


def _timing_metrics(sta_text: str, sta_summary_text: str) -> dict[str, float | None]:
    clock_match = re.search(
        r"^;\s*dynamic_memory_clk\s*;\s*Base\s*;\s*([\d.]+)\s*;",
        sta_text,
        flags=re.MULTILINE,
    )
    fmax_match = re.search(
        r"Slow\s+\d+mV\s+85C Model Fmax Summary.*?"
        r"^;\s*([\d.]+) MHz\s*;\s*([\d.]+) MHz\s*;\s*dynamic_memory_clk\s*;",
        sta_text,
        flags=re.MULTILINE | re.DOTALL,
    )
    slack_match = re.search(
        r"Type\s*:\s*Slow\s+\d+mV\s+85C Model Setup 'dynamic_memory_clk'\s*\n"
        r"Slack\s*:\s*(-?[\d.]+)",
        sta_summary_text,
    )
    return {
        "clock_period_ns": float(clock_match.group(1)) if clock_match else None,
        "fmax_mhz": float(fmax_match.group(1)) if fmax_match else None,
        "restricted_fmax_mhz": float(fmax_match.group(2)) if fmax_match else None,
        "worst_setup_slack_ns": float(slack_match.group(1)) if slack_match else None,
    }


def collect(build_dir: Path) -> dict[str, object]:
    build_dir = build_dir.resolve()
    output_dir = build_dir / "output_files"
    if not output_dir.is_dir():
        raise ValueError(f"missing Quartus output directory: {output_dir}")

    fit_path = _first_report(output_dir, "fit.summary")
    sta_summary_path = _first_report(output_dir, "sta.summary")
    sta_path = _first_report(output_dir, "sta.rpt")
    flow_path = _first_report(output_dir, "flow.rpt")

    fit = _summary_fields(fit_path.read_text(encoding="utf-8", errors="replace"))
    sta_text = sta_path.read_text(encoding="utf-8", errors="replace")
    sta_summary_text = sta_summary_path.read_text(encoding="utf-8", errors="replace")
    flow_text = flow_path.read_text(encoding="utf-8", errors="replace")
    timing = _timing_metrics(sta_text, sta_summary_text)

    row: dict[str, object] = {
        "variant": build_dir.name,
        "flow_status": fit.get("Fitter Status", "unknown").split(" - ", 1)[0],
        "quartus_version": fit.get("Quartus Prime Version", "unknown"),
        "family": fit.get("Family", "unknown"),
        "device": fit.get("Device", "unknown"),
        "logic_elements": _leading_integer(fit["Total logic elements"]),
        "combinational_functions": _leading_integer(
            fit["Total combinational functions"]
        ),
        "dedicated_logic_registers": _leading_integer(
            fit["Dedicated logic registers"]
        ),
        "total_registers": _leading_integer(fit["Total registers"]),
        "memory_bits": _leading_integer(fit["Total memory bits"]),
        "multipliers_9bit": _leading_integer(
            fit["Embedded Multiplier 9-bit elements"]
        ),
        "flow_elapsed_s": _elapsed_seconds(flow_text),
        **timing,
    }
    return {field: row.get(field) for field in CSV_FIELDS}


def write_csv(rows: Iterable[dict[str, object]], destination: Path | None) -> None:
    stream = (
        destination.open("w", newline="", encoding="utf-8")
        if destination
        else sys.stdout
    )
    try:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    finally:
        if destination:
            stream.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build_dirs", nargs="+", type=Path)
    parser.add_argument("--output", "-o", type=Path, help="CSV path (default: stdout)")
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit JSON instead of CSV (ignores --output)",
    )
    args = parser.parse_args()

    try:
        rows = [collect(path) for path in args.build_dirs]
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
            write_csv(rows, args.output)
    except (OSError, KeyError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
