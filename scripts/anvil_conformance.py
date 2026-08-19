#!/usr/bin/env python3
"""Run positive/negative fixtures against the experimental Anvil compiler.

Current Anvil JSON mode reports semantic success in a JSON field and may return
status 0 for a rejected input. This harness therefore treats `success` as the
oracle while retaining the raw process status as drift information.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
COMPILER_TIMEOUT_SECONDS = 120


def compiler_command() -> list[str]:
    configured = os.environ.get("ANVIL_COMMAND")
    if configured:
        command = shlex.split(configured)
    else:
        command = [os.environ.get("ANVIL_BIN", "anvil")]

    if not command:
        raise FileNotFoundError("ANVIL_COMMAND is empty")

    executable = command[0]
    if os.path.sep not in executable and shutil.which(executable) is None:
        raise FileNotFoundError(
            "Anvil compiler not found. Set ANVIL_BIN=/path/to/anvil or "
            "ANVIL_COMMAND='dune exec anvil --'."
        )
    if os.path.sep in executable and not Path(executable).is_file():
        raise FileNotFoundError(f"Anvil compiler does not exist: {executable}")
    return command


def parse_json_output(stdout: str) -> dict[str, Any]:
    candidates = [line.strip() for line in stdout.splitlines() if line.strip()]
    for candidate in reversed(candidates):
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and isinstance(value.get("success"), bool):
            return value
    raise ValueError("compiler output did not contain an Anvil JSON result")


def diagnostic_text(result: dict[str, Any]) -> str:
    fragments: list[str] = []
    for error in result.get("errors", []):
        if not isinstance(error, dict):
            continue
        for fragment in error.get("description", []):
            if isinstance(fragment, dict) and isinstance(fragment.get("text"), str):
                fragments.append(fragment["text"])
    return "\n".join(fragments)


def run_case(command: list[str], case: dict[str, Any]) -> tuple[bool, str]:
    source = ROOT / case["path"]
    try:
        completed = subprocess.run(
            [*command, "-json", "-just-check", str(source)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=COMPILER_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return False, f"compiler timed out after {COMPILER_TIMEOUT_SECONDS} seconds"
    try:
        result = parse_json_output(completed.stdout)
    except ValueError as error:
        detail = completed.stderr.strip() or completed.stdout.strip() or str(error)
        return False, f"unparseable compiler result (exit={completed.returncode}): {detail}"

    expected_success = case["expect"] == "pass"
    if result["success"] is not expected_success:
        return (
            False,
            f"expected {case['expect']}, got success={result['success']} "
            f"(exit={completed.returncode})",
        )

    if expected_success and completed.returncode != 0:
        return (
            False,
            "compiler reported success but returned unexpected process "
            f"exit={completed.returncode}",
        )
    if not expected_success and completed.returncode not in (0, 1):
        return (
            False,
            "compiler reported a source rejection but returned unexpected "
            f"process exit={completed.returncode}",
        )

    required = case.get("diagnostic_any", [])
    diagnostics = diagnostic_text(result)
    if required and not any(fragment in diagnostics for fragment in required):
        return False, f"missing expected diagnostic; received: {diagnostics or '<none>'}"

    exit_note = f", process exit={completed.returncode}"
    return True, f"{case['concept']}{exit_note}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "anvil" / "manifest.json",
        help="fixture manifest (default: anvil/manifest.json)",
    )
    args = parser.parse_args(argv)

    try:
        command = compiler_command()
    except FileNotFoundError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    failures = 0
    for case in manifest["cases"]:
        passed, detail = run_case(command, case)
        marker = "PASS" if passed else "FAIL"
        print(f"[{marker}] {case['path']}: {detail}")
        failures += not passed

    total = len(manifest["cases"])
    print(f"\n{total - failures}/{total} fixtures matched their expectations")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
