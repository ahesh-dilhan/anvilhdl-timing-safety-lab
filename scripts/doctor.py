#!/usr/bin/env python3
"""Report the host capabilities used by this lab without installing anything."""

from __future__ import annotations

import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys


TOOLS = (
    ("python3", True, "dependency-free model and tests", ()),
    ("make", True, "repository task runner", ()),
    ("anvil", False, "official-compiler fixture checks", ()),
    ("opam", False, "building the official Anvil compiler", ()),
    ("dune", False, "building the official Anvil compiler", ()),
    ("iverilog", False, "portable RTL benchmark simulation", ()),
    ("verilator", False, "generated-SystemVerilog simulation", ()),
    ("gtkwave", False, "viewing generated VCD waveforms", ()),
    (
        "vsim",
        False,
        "Questa simulation (a license environment is also required)",
        (str(Path.home() / "intelFPGA_lite/21.1/questa_fse/linux_x86_64/vsim"),),
    ),
    ("quartus_sh", False, "pinned FPGA structural comparison", ()),
    (
        "vivado",
        False,
        "optional Xilinx synthesis and simulation",
        ("/tools/Xilinx/2025.2/Vivado/bin/vivado",),
    ),
    (
        "vitis-run",
        False,
        "optional HLS learning exercises",
        ("/tools/Xilinx/2025.2/Vitis/bin/vitis-run",),
    ),
    ("yosys", False, "open-source synthesis proxy", ()),
)


def resolve_executable(name: str, candidates: tuple[str, ...]) -> str | None:
    discovered = shutil.which(name)
    if discovered:
        return discovered
    for candidate in candidates:
        path = Path(candidate)
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
    return None


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
        if completed.returncode != 0:
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
    for name, required, purpose, candidates in TOOLS:
        path = resolve_executable(name, candidates)
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
