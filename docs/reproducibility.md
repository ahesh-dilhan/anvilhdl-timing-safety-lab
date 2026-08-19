# Reproducibility guide

## Tier 1: dependency-free model

Requirements: Python 3.11 or newer and GNU Make.

```bash
make doctor
make test
make demo
```

Direct invocation is useful when debugging:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m anvil_lab experiments/01_safe_dynamic_cache.json
```

The experiments are deterministic: the checker enumerates an ordered Cartesian
product rather than sampling random delays.

## Tier 2: official Anvil compiler fixtures

The optional integration uses the official repository and exact revision in
`UPSTREAM.lock`. Upstream currently documents OCaml 5.2.0, Opam, Dune, and
Verilator 5.024.

With an `anvil` executable already installed:

```bash
ANVIL_BIN=/path/to/anvil make anvil-check
```

The harness treats an expected compiler rejection as a successful negative
test. Accepted inputs must both report JSON success and exit 0. Rejected inputs
must report JSON failure, return 0 (the pinned compiler's current quirk) or 1,
and match a stable diagnostic category rather than a complete message snapshot.

## Updating the upstream pin

1. Read the release/commit changes between the old and proposed revisions.
2. Replace `revision=` in `UPSTREAM.lock` with the full 40-character SHA.
3. Rebuild the compiler in a clean environment.
4. Run all positive and negative fixtures.
5. Record the reason and any diagnostic changes in the commit message.

Never silently track `master`: a moving dependency makes compiler regressions
and language changes indistinguishable from changes in this lab.

## Recording future synthesis or simulation results

Do not hand-edit performance numbers into the README. A result record should
include at least:

- repository commit;
- official Anvil commit;
- compiler flags (`-O 0`, `-O 1`, or `-O 2`);
- simulator/synthesis tool and version;
- exact command and deterministic seed, if any;
- generated SystemVerilog checksum;
- measured metric and unit.

Until those tools have been run, mark the corresponding result **not run**.
The paper's commercial 22-nm measurements are context, not results reproduced
by this repository.
