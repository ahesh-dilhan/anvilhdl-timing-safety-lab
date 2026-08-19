# Upstream landscape

Observed on 20 August 2026. AnvilHDL is experimental and active, so every
integration result should record a commit rather than rely on the label
“version 0.1.0.”

## Public surfaces

| Surface | Location | Observed revision/status |
| --- | --- | --- |
| Compiler | [kisp-nus/anvil](https://github.com/kisp-nus/anvil) | `d138cab`, 5 Aug 2026; MIT; active experimental project |
| Documentation | [docs.anvil.kisp-lab.org](https://docs.anvil.kisp-lab.org/) | Site labels itself 0.1.0 |
| Playground | [anvil.kisp-lab.org](https://anvil.kisp-lab.org/) | UI reports compiler `ed8b8d4` (Dec 2025) |
| Paper artifact | [kisp-nus/AnvilHDL-Experiments](https://github.com/kisp-nus/AnvilHDL-Experiments) | Pins compiler `d4241cb` plus benchmark revisions |

The paper's `jasonyu1996/anvil` link now redirects to the NUS KISP organization.
The different compiler revisions across source, playground, and artifact make
version-aware bug reports and regression records especially important.

## Reproduction boundary

The official artifact documents a substantial container build and provides
benchmark execution, sample output, and existing synthesis reports. It does not
include the commercial 22-nm PDK/toolchain used to independently regenerate the
paper's area and power table. An open-source Yosys experiment would therefore
be a new proxy study, not a reproduction of Table 1.

## Current integration details

At the pinned current revision:

- `lib/config.ml` exposes `-json`; the repository README still says
  `-json-output`.
- `bin/main.ml` prints `{"success": false, ...}` for a compilation error in
  JSON mode without calling `exit 1` in that error branch.
- `run-tests.py` prints a summary but does not propagate the number of failed
  cases as its process status.

The conformance harness in this repository therefore parses the JSON `success`
field. This is more reliable than assuming that exit code 0 means accepted.

## Nearby active work

- [Issue #77](https://github.com/kisp-nus/anvil/issues/77) tracks examples that
  broke under stricter checking.
- [Issue #87](https://github.com/kisp-nus/anvil/issues/87) records an operator
  associativity problem.
- [PR #83](https://github.com/kisp-nus/anvil/pull/83) concerns AST/LSP work.
- Draft [PR #86](https://github.com/kisp-nus/anvil/pull/86) explores Anvil/
  SystemVerilog assertion generation.

New work should complement these efforts rather than claim novelty by
duplicating them.

## Follow-on research context

[Pact: Language-based Hardware Communication Safety and
Liveness](https://capra.cs.cornell.edu/latte26/paper/latte26-final29.pdf) extends
the line of work with session types for communication safety and progress properties.
That separation reinforces an important reading of the Anvil result: timing
safety alone is not a deadlock-freedom theorem.
