"""Command-line interface for the bounded timing-safety lab."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Sequence, TextIO

from .loader import ScenarioFormatError, load_scenario
from .model import ModelError
from .oracle import AnalysisResult, TimingSafetyOracle, Violation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="anvil-lab",
        description=(
            "Enumerate bounded event schedules and check pedagogical timing-safety "
            "obligations. With no file arguments, all JSON files in experiments/ "
            "are analyzed."
        ),
    )
    parser.add_argument("files", nargs="*", type=Path, help="scenario JSON file(s)")
    parser.add_argument(
        "--all",
        action="store_true",
        help="analyze every *.json file in the experiments directory",
    )
    parser.add_argument(
        "--experiments-dir",
        type=Path,
        default=Path("experiments"),
        help="experiment directory used by --all (default: experiments)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="emit machine-readable JSON",
    )
    parser.add_argument(
        "--show-schedules",
        action="store_true",
        help="include every enumerated schedule in JSON output",
    )
    parser.add_argument(
        "--max-schedules",
        type=int,
        default=10_000,
        help="refuse scenarios above this exhaustive bound (default: 10000)",
    )
    parser.add_argument(
        "--fail-on-unsafe",
        action="store_true",
        help="return status 1 when any scenario is unsafe",
    )
    parser.add_argument(
        "--fail-on-mismatch",
        action="store_true",
        help="return status 1 only when an expected safe/unsafe result is wrong",
    )
    return parser


def _select_paths(args: argparse.Namespace) -> list[Path]:
    if args.all and args.files:
        raise ScenarioFormatError("--all cannot be combined with explicit files")
    if args.all or not args.files:
        directory: Path = args.experiments_dir
        if not directory.is_dir():
            raise ScenarioFormatError(f"experiment directory does not exist: {directory}")
        paths = sorted(directory.glob("*.json"))
        if not paths:
            raise ScenarioFormatError(f"no JSON experiments found in {directory}")
        return paths
    return list(args.files)


def _format_schedule(result: AnalysisResult, index: int) -> str:
    schedule = result.schedules[index - 1]
    events = ", ".join(f"{name}={time}" for name, time in schedule.times.items())
    dynamic = ", ".join(
        f"{name}:{delay}"
        for name, delay in schedule.delays.items()
        if not next(
            event for event in result.scenario.dag.events if event.name == name
        ).delay.is_fixed
    )
    return f"events {{{events}}}" + (f"; dynamic delays {{{dynamic}}}" if dynamic else "")


def render_readable(results: Sequence[AnalysisResult], stream: TextIO) -> None:
    for result_index, result in enumerate(results):
        if result_index:
            print(file=stream)
        status = "BOUNDED SAFE" if result.safe else "UNSAFE"
        expectation = ""
        if result.scenario.expected_safe is not None:
            expected = (
                "BOUNDED SAFE" if result.scenario.expected_safe else "UNSAFE"
            )
            marker = "matches" if result.expectation_matches else "MISMATCH"
            expectation = f"; expected {expected} ({marker})"
        print(
            f"[{status}] {result.scenario.name}: "
            f"{result.schedules_checked} schedule(s) checked{expectation}",
            file=stream,
        )
        if result.scenario.description:
            print(f"  {result.scenario.description}", file=stream)

        if result.violations:
            grouped: dict[tuple[str, ...], list[Violation]] = defaultdict(list)
            for violation in result.violations:
                grouped[violation.check_id].append(violation)
            for failures in grouped.values():
                witness = failures[0]
                print(
                    f"  - {witness.kind}: {witness.message} "
                    f"({len(failures)}/{result.schedules_checked} schedules; "
                    f"witness #{witness.schedule_index})",
                    file=stream,
                )
                print(
                    f"    {_format_schedule(result, witness.schedule_index)}",
                    file=stream,
                )

    safe_count = sum(result.safe for result in results)
    unsafe_count = len(results) - safe_count
    mismatch_count = sum(result.expectation_matches is False for result in results)
    print(file=stream)
    print(
        f"Summary: {len(results)} scenario(s), {safe_count} bounded safe, "
        f"{unsafe_count} unsafe, {mismatch_count} expectation mismatch(es).",
        file=stream,
    )


def render_json(
    results: Sequence[AnalysisResult], include_schedules: bool, stream: TextIO
) -> None:
    payload = {
        "schema_version": 1,
        "summary": {
            "scenarios": len(results),
            "safe": sum(result.safe for result in results),
            "unsafe": sum(not result.safe for result in results),
            "expectation_mismatches": sum(
                result.expectation_matches is False for result in results
            ),
        },
        "results": [
            result.to_dict(include_schedules=include_schedules) for result in results
        ],
    }
    json.dump(payload, stream, indent=2, sort_keys=True)
    print(file=stream)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        paths = _select_paths(args)
        oracle = TimingSafetyOracle(max_schedules=args.max_schedules)
        results = [oracle.analyze(load_scenario(path)) for path in paths]
    except (ScenarioFormatError, ModelError) as exc:
        print(f"anvil-lab: error: {exc}", file=sys.stderr)
        return 2

    if args.json_output:
        render_json(results, include_schedules=args.show_schedules, stream=sys.stdout)
    else:
        render_readable(results, stream=sys.stdout)

    if args.fail_on_unsafe and any(not result.safe for result in results):
        return 1
    if args.fail_on_mismatch and any(
        result.expectation_matches is False for result in results
    ):
        return 1
    return 0
