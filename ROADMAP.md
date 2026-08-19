# Roadmap

The first milestone is intentionally small and testable. Later milestones are
listed as planned until their commands have actually run and produced recorded
evidence.

## Milestone 1 — executable paper study

- [x] Bounded event-DAG schedule enumeration
- [x] Half-open event-relative interval model
- [x] Valid value-use checks
- [x] Register mutation versus loan-time checks
- [x] Message source-lifetime and non-overlap checks
- [x] Safe/unsafe dynamic-latency litmus scenarios
- [x] Dependency-free unit tests and CI matrix
- [x] Section-grounded paper notes and research discussion guide

## Milestone 2 — pinned compiler conformance

- [x] Current upstream revision lock
- [x] JSON-aware positive/negative fixture harness
- [x] Run every fixture against the pinned compiler in GitHub Actions (5/5)
- [ ] Add a second profile for the paper-artifact compiler revision
- [ ] Record normalized diagnostic categories and source spans
- [ ] Track intentional cross-revision differences as XFAIL, not silent skips

## Milestone 3 — RTL boundary experiment

- [ ] Generate SystemVerilog for the safe dynamic-memory client
- [ ] Connect it to a handwritten variable-latency memory
- [ ] Inject deterministic backpressure/latency sequences
- [ ] Check data stability while a transaction is pending
- [ ] Store VCD checksum, seed, compiler SHA, and tool versions

## Milestone 4 — optimizer differential test

- [ ] Compile branch/join-heavy cases at `-O 0`, `-O 1`, and `-O 2`
- [ ] Compare cycle traces across optimization levels
- [ ] Run an open-source Yosys/ABC cell-count proxy
- [ ] Distinguish proxy results from the paper's commercial 22-nm results

## Research extensions

- [ ] Generate minimal event graphs for differential checking against Anvil
- [ ] Measure conservative rejection patterns in order analysis
- [ ] Explore richer contracts at the SystemVerilog boundary
- [ ] Build a timing-safe but deadlocked example to separate safety from liveness
- [ ] Evaluate whether a minimized concrete witness improves compiler diagnostics

Potential work should be checked against current upstream issues and pull
requests before implementation to avoid duplicating active maintainers' work.
