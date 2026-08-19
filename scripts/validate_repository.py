#!/usr/bin/env python3
"""Validate repository metadata, scenario files, fixture paths, and local links."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from anvil_lab.loader import ScenarioFormatError, load_scenario  # noqa: E402


LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
SHA40 = re.compile(r"^[0-9a-f]{40}$")


def read_lock() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in (ROOT / "UPSTREAM.lock").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"malformed UPSTREAM.lock line: {line}")
        key, value = line.split("=", 1)
        values[key] = value
    required = {"repository", "revision", "observed_at", "paper"}
    missing = required - values.keys()
    if missing:
        raise ValueError(f"UPSTREAM.lock is missing: {', '.join(sorted(missing))}")
    if not SHA40.fullmatch(values["revision"]):
        raise ValueError("UPSTREAM.lock revision must be a full lowercase SHA")
    return values


def validate_manifest() -> int:
    path = ROOT / "anvil" / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise ValueError("unsupported anvil manifest schema")
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("anvil manifest needs at least one case")
    seen: set[str] = set()
    for case in cases:
        source = case.get("path")
        if not isinstance(source, str) or source in seen:
            raise ValueError(f"invalid or duplicate fixture path: {source!r}")
        seen.add(source)
        if not (ROOT / source).is_file():
            raise ValueError(f"fixture does not exist: {source}")
        if case.get("expect") not in {"pass", "fail"}:
            raise ValueError(f"fixture has invalid expectation: {source}")
    discovered = {
        str(path.relative_to(ROOT)) for path in (ROOT / "anvil").rglob("*.anvil")
    }
    if seen != discovered:
        missing = sorted(discovered - seen)
        extra = sorted(seen - discovered)
        details: list[str] = []
        if missing:
            details.append(f"unlisted fixtures: {', '.join(missing)}")
        if extra:
            details.append(f"manifest-only fixtures: {', '.join(extra)}")
        raise ValueError("fixture manifest mismatch: " + "; ".join(details))
    return len(cases)


def validate_workflow_pin(lock: dict[str, str]) -> None:
    workflow = (ROOT / ".github/workflows/anvil-integration.yml").read_text(
        encoding="utf-8"
    )
    block_match = re.search(
        r"(?ms)^\s*- name: Check out pinned AnvilHDL\s*$"
        r"(?P<block>.*?)^\s*- name: ",
        workflow,
    )
    if block_match is None:
        raise ValueError("Anvil integration workflow lacks a pinned checkout step")
    block = block_match.group("block")
    repository_match = re.search(r"(?m)^\s*repository:\s*([^\s#]+)", block)
    revision_match = re.search(r"(?m)^\s*ref:\s*([^\s#]+)", block)
    if repository_match is None or revision_match is None:
        raise ValueError("pinned checkout must declare repository and ref")

    expected_repository = lock["repository"].removesuffix(".git").removeprefix(
        "https://github.com/"
    )
    if repository_match.group(1) != expected_repository:
        raise ValueError("Anvil workflow repository does not match UPSTREAM.lock")
    if revision_match.group(1) != lock["revision"]:
        raise ValueError("Anvil workflow revision does not match UPSTREAM.lock")


def validate_scenarios() -> int:
    paths = sorted((ROOT / "experiments").glob("*.json"))
    if not paths:
        raise ValueError("no experiment scenarios found")
    names: set[str] = set()
    for path in paths:
        try:
            scenario = load_scenario(path)
        except ScenarioFormatError as error:
            raise ValueError(str(error)) from error
        if scenario.name in names:
            raise ValueError(f"duplicate scenario name: {scenario.name}")
        names.add(scenario.name)
        if scenario.expected_safe is None:
            raise ValueError(f"scenario lacks an expected result: {path.name}")
    return len(paths)


def validate_local_links() -> int:
    checked = 0
    markdown_files = [ROOT / "README.md", ROOT / "ROADMAP.md"]
    markdown_files.extend(sorted((ROOT / "docs").glob("*.md")))
    markdown_files.extend(sorted((ROOT / "anvil").glob("*.md")))
    for document in markdown_files:
        text = document.read_text(encoding="utf-8")
        for match in LINK.finditer(text):
            target = match.group(1).strip()
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = target.split("#", 1)[0]
            if not target:
                continue
            resolved = (document.parent / target).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError as error:
                raise ValueError(
                    f"local link escapes repository in {document.relative_to(ROOT)}: {target}"
                ) from error
            if not resolved.exists():
                raise ValueError(
                    f"broken local link in {document.relative_to(ROOT)}: {target}"
                )
            checked += 1
    return checked


def main() -> int:
    try:
        lock = read_lock()
        validate_workflow_pin(lock)
        fixture_count = validate_manifest()
        scenario_count = validate_scenarios()
        link_count = validate_local_links()
        pdfs = list(ROOT.rglob("*.pdf"))
        if pdfs:
            raise ValueError("do not vendor paper PDFs; cite the canonical URL")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"repository validation failed: {error}", file=sys.stderr)
        return 1

    print(
        f"repository metadata valid: {scenario_count} scenarios, "
        f"{fixture_count} Anvil fixtures, {link_count} local links"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
