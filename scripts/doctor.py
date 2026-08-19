#!/usr/bin/env python3
"""Report the host capabilities used by this lab without installing anything."""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys


TOOLS = (
    ("python3", True, "dependency-free model and tests"),
    ("make", True, "repository task runner"),
    ("anvil", False, "official-compiler fixture checks"),
    ("opam", False, "building the official Anvil compiler"),
    ("dune", False, "building the official Anvil compiler"),
    ("verilator", False, "generated-SystemVerilog simulation"),
    ("iverilog", False, "small RTL simulations"),
    ("yosys", False, "open-source synthesis proxy"),
)


def first_version_line(executable: str) -> str:
    for flag in ("--version", "-version", "version"):
        try:
            completed = subprocess.run(
                [executable, flag],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=3,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        output = completed.stdout.strip().splitlines()
        if output:
            return output[0]
    return "version unavailable"


def main() -> int:
    print(f"Host: {platform.platform()}")
    print(f"Python runtime: {platform.python_version()}")
    print()

    required_missing = False
    for name, required, purpose in TOOLS:
        path = shutil.which(name)
        status = "required" if required else "optional"
        if path:
            print(f"[FOUND]   {name:<10} {first_version_line(path)}")
        else:
            print(f"[MISSING] {name:<10} ({status}: {purpose})")
            required_missing |= required

    if sys.version_info < (3, 11):
        print("\nERROR: Python 3.11 or newer is required.", file=sys.stderr)
        required_missing = True

    if not required_missing:
        print("\nCore model prerequisites are ready. Missing optional tools do not block `make test`.")
    return 1 if required_missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
