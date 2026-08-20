# Dynamic-memory benchmark result record

This directory records evidence produced by the protocol in
[`docs/dynamic-memory-benchmark.md`](../../../docs/dynamic-memory-benchmark.md).
Unmeasured fields are intentionally marked **not run**. Replace them only when
the referenced log, waveform, report, and provenance are available.

## Provenance

| Field | Recorded value |
| --- | --- |
| UTC timestamp | 2026-08-20T05:59:14Z |
| Repository commit | Working-tree run based on `2018500`; source hashes are in [`behavioral_summary.json`](behavioral_summary.json) |
| Repository clean/dirty state | New benchmark files under review at measurement time |
| Anvil revision | `d138cabedbfc3b65c08249ce6a55cb90dad959da` |
| Anvil command and flags | Previously verified by the pinned integration workflow; this RTL run did not invoke Anvil |
| Simulator and version | Icarus Verilog 12.0 (`12.0-2build2`) |
| Simulation command | `make rtl-demo` (equivalent environment overrides were used for a temporarily unpacked package) |
| Quartus version | 21.1.0 Build 842 Lite Edition (structural run) |
| FPGA part | Cyclone IV E `EP4CE115F29C7` (structural run) |
| Clock constraint | 20 ns / 50 MHz on `clk`; internal register paths only |
| Host/OS | Linux 7.0.0-29-generic, x86_64 |

## Behavioral results

| Case | Source artifact | Expected observation | Observed status | Latencies explored | Transactions | Mismatches | First failure | Evidence |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- |
| Naive SystemVerilog | [`rtl/unsafe_dynamic_memory_client.sv`](../rtl/unsafe_dynamic_memory_client.sv) | Compiles; longer latency exposes stability error | Expected failure observed | `1, 2, 3, 4, 1, 4` | 6 | 4 | Cycle 5, address stability | [`iverilog_12_reference.txt`](iverilog_12_reference.txt) |
| Safe SystemVerilog + monitor | [`rtl/safe_dynamic_memory_client.sv`](../rtl/safe_dynamic_memory_client.sv) | Passes configured schedules | Pass | `1, 2, 3, 4, 1, 4` | 6 | 0 | N/A | [`measured_behavioral_results.csv`](measured_behavioral_results.csv) |
| Unsafe Anvil | [`anvil/unsafe/mutate_while_loaned.anvil`](../../../anvil/unsafe/mutate_while_loaned.anvil) | Rejected: borrowed-register mutation | Rejected in pinned integration | N/A | N/A | N/A | N/A | [`anvil/manifest.json`](../../../anvil/manifest.json) |
| Safe Anvil | [`anvil/safe/dynamic_memory_client.anvil`](../../../anvil/safe/dynamic_memory_client.anvil) | Accepted | Accepted in pinned integration | N/A | N/A | N/A | N/A | [`anvil/manifest.json`](../../../anvil/manifest.json) |

For a behavioral failure, record the cycle and violated rule as well as the
latency vector or deterministic seed. A screenshot is supplementary evidence;
retain the machine-readable log and waveform too.

## Quartus implementation results

| Variant | Input RTL | Top | Optimization | Logic elements | Combinational functions | Registers | Memory bits | 9-bit multipliers | Worst setup slack | Raw / restricted Fmax | Compile time | Report |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Naive SystemVerilog | [`rtl/unsafe_dynamic_memory_client.sv`](../rtl/unsafe_dynamic_memory_client.sv) | `unsafe_dynamic_memory_client` | N/A | 22 | 22 | 15 | 0 | 0 | 17.289 ns | 368.87 / 250.00 MHz | 14 s | [`measured_results.csv`](../quartus/measured_results.csv) |
| Safe SystemVerilog | [`rtl/safe_dynamic_memory_client.sv`](../rtl/safe_dynamic_memory_client.sv) | `safe_dynamic_memory_client` | N/A | 18 | 18 | 13 | 0 | 0 | 17.765 ns | 447.43 / 250.00 MHz | 15 s | [`measured_results.csv`](../quartus/measured_results.csv) |
| Unsafe Anvil | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | Compiler rejection expected |
| Safe Anvil generated SV | not run | not run | `-O 0` | not run | not run | not run | not run | not run | not run | not run | not run | not run |
| Safe Anvil generated SV | not run | not run | `-O 1` | not run | not run | not run | not run | not run | not run | not run | not run | not run |
| Safe Anvil generated SV | not run | not run | `-O 2` | not run | not run | not run | not run | not run | not run | not run | not run | not run |

If the Anvil-generated module and hand-written SystemVerilog clients do not use
the same wrapper and workload, split their measurements into separate tables.
Do not calculate percentage deltas between incomparable rows.

## Artifact integrity

Record SHA-256 checksums after producing artifacts:

| Artifact | SHA-256 |
| --- | --- |
| Stimulus/latency schedule | Source hashes recorded in [`behavioral_summary.json`](behavioral_summary.json) |
| Combined simulation log | `b5d4104a471590405f707bd148d231c58f6d38f4e3cefd1a85fa43f4f9bcb146` |
| Combined safe/counterexample waveform | Normalized trace: `469370eb0083fac2cdf5cdb33f528a30a48975484318923dfc46e188960a45f7` (the wall-clock `$date` block is excluded) |
| Anvil conformance JSON/log | not run |
| Generated SystemVerilog (`-O 0`) | not run |
| Generated SystemVerilog (`-O 1`) | not run |
| Generated SystemVerilog (`-O 2`) | not run |
| Quartus raw reports | Run successfully but not retained or hashed; regenerate them with `make synth-quartus` |
| Parsed Quartus result CSV | `173589da535232adba2590dfcf7605524db45aae3ba32de3aad1f9ac1fa7bd3f` |

## Completion checklist

- [ ] Configuration and expected outcomes were written before inspecting results.
- [x] Both SystemVerilog clients used the same memory, stimuli, and checks.
- [x] Every configured latency was exercised deterministically.
- [x] The first counterexample was retained with its causal signals.
- [x] Anvil results came from the revision recorded above.
- [x] Synthesis rows used one Quartus version, part, and clock constraint.
- [x] Simulation-only monitors were excluded consistently from synthesis.
- [x] No finite test pass is described as proof.
- [x] Every reported number points to a compact record or regenerating command.
