# Dynamic-memory timing-safety benchmark

## Research question

Can a small variable-latency memory example expose the difference between
detecting a cross-cycle stability bug during selected RTL executions and
rejecting the corresponding register-lifetime violation before simulation?

The benchmark studies one obligation: after a client presents an address, that
address must remain stable until the response event releases it. A memory
response may take different numbers of cycles, so passing the one-cycle case
does not establish that the client obeys the obligation.

## Four cases

| Case | Mechanism under study | Expected observation |
| --- | --- | --- |
| Naive SystemVerilog | [`unsafe_dynamic_memory_client.sv`](../benchmarks/dynamic_memory/rtl/unsafe_dynamic_memory_client.sv) changes its address using a fixed-cycle assumption. | The HDL compiles; the monitor reports a mismatch or stability violation when a selected response latency outlives that assumption. |
| Safe SystemVerilog + monitor | [`safe_dynamic_memory_client.sv`](../benchmarks/dynamic_memory/rtl/safe_dynamic_memory_client.sv) holds the outstanding address until response; an implementation-specific monitor checks the rule. | All enumerated test schedules complete without a scoreboard or monitor failure. |
| Unsafe Anvil | [`anvil/unsafe/mutate_while_loaned.anvil`](../anvil/unsafe/mutate_while_loaned.anvil) writes the address register while the request still loans it. | The official compiler rejects the program with the stable diagnostic category `Attempted assignment to a borrowed register`. |
| Safe Anvil | [`anvil/safe/dynamic_memory_client.anvil`](../anvil/safe/dynamic_memory_client.anvil) waits for the response before updating the address. | The official compiler accepts the program at the pinned revision. |

The existing bounded scenarios are useful explanatory companions:
[`experiments/02_early_address_mutation.json`](../experiments/02_early_address_mutation.json)
enumerates the unsafe scheduling pattern, while
[`experiments/01_safe_dynamic_cache.json`](../experiments/01_safe_dynamic_cache.json)
models the corresponding safe loan boundary. They are not replacements for RTL
simulation or the Anvil compiler.

The Anvil fixtures and SystemVerilog clients express the same lifetime question,
but they should not be described as cycle-accurate equivalent implementations
unless a shared wrapper, transaction trace, and equivalence check are added.

## Repository layout and quick run

[`variable_latency_memory.sv`](../benchmarks/dynamic_memory/rtl/variable_latency_memory.sv)
is shared by both clients, and
[`tb_dynamic_memory.sv`](../benchmarks/dynamic_memory/tb/tb_dynamic_memory.sv)
applies six requests with the latency sequence `1, 2, 3, 4, 1, 4` and common
checks. From the repository root, the portable entry point is:

```bash
benchmarks/dynamic_memory/sim/run_iverilog.sh
```

[`run_questa.sh`](../benchmarks/dynamic_memory/sim/run_questa.sh) is the
alternative Questa entry point when a valid license is configured. A successful
run writes its log and `dynamic_memory.vcd` below `sim/generated/` for waveform
inspection. These are generated results rather than source files; the
simulation log is the primary pass/fail record.

## Experimental protocol

1. Pin the repository revision and the Anvil revision recorded in
   [`UPSTREAM.lock`](../UPSTREAM.lock). Record simulator and FPGA tool versions.
2. Use the same address width, data function, reset convention, request stream,
   and deterministic latency schedule for both SystemVerilog clients.
3. Include latency one as the tempting passing case and every configured longer
   latency. Prefer an exhaustive small grid, such as response latency 1--4,
   over unrecorded random testing.
4. Use one scoreboard for returned address/data order and a separate monitor for
   the stability rule: while a request is outstanding, the captured request
   address must not change before response completion.
5. Run the naive client first and preserve the shortest failing trace. Then run
   the safe client without changing the memory model, stimuli, or checks.
6. Run the official compiler fixtures through the manifest harness. Judge a
   negative fixture from the compiler's JSON `success` field and normalized
   diagnostic, not process status alone.
7. Save the exact command, log, waveform, deterministic schedule or seed, and
   SHA-256 checksum of generated SystemVerilog beside each result.

Before a run, define these failure conditions:

- a returned word differs from the scoreboard's expected word;
- a response is missing, duplicated, or reordered;
- the request address changes while the stability monitor is active;
- the run times out with an outstanding request; or
- observed Anvil acceptance differs from the fixture manifest.

## Measurements

The behavioral table should report case status, explored latency values,
completed transactions, mismatch count, first failing cycle, and the violated
rule. A counterexample is more useful when it includes the minimal signal set:

```text
clock  reset  request  request_ready  address
response  response_valid  response_data  outstanding  violation
```

For synthesis, record the target part, clock constraint, compiler options,
logic elements or ALMs, registers, memory bits, worst setup slack or Fmax, and
wall-clock compile time. Do not compare resource numbers obtained from different
FPGA families or synthesis tools as if they used a common unit.

Fields without supporting artifacts in the neutral record at
[`benchmarks/dynamic_memory/results/README.md`](../benchmarks/dynamic_memory/results/README.md)
should remain marked **not run** until their supporting artifacts exist.

## Optional Quartus comparison

The current structural flow is documented in
[`benchmarks/dynamic_memory/quartus/README.md`](../benchmarks/dynamic_memory/quartus/README.md).
It uses Quartus Prime Lite 21.1, Cyclone IV E `EP4CE115F29C7`, a 20 ns
(`50 MHz`) clock on `clk`, and fitter seed 1 for both SystemVerilog clients.
Run either variant through
[`run_variant.sh`](../benchmarks/dynamic_memory/quartus/run_variant.sh), then
extract comparable fields with
[`collect_results.py`](../benchmarks/dynamic_memory/quartus/collect_results.py).
The checked-in parsed record is
[`measured_results.csv`](../benchmarks/dynamic_memory/quartus/measured_results.csv).

Synthesize design logic with simulation-only monitors excluded consistently.
The supplied constraint covers internal register-to-register paths; its Fmax
and setup slack are useful structural observations, not board timing sign-off.
The unsafe Anvil row is `N/A`: rejection is the intended result, so there is no
valid generated RTL to synthesize.

| Variant | Source status | Anvil optimization | Logic elements | Registers | Memory bits | 9-bit multipliers | Setup slack / raw path Fmax | Compile time |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Naive SystemVerilog | compilable but protocol-unsafe | N/A | 22 | 15 | 0 | 0 | 17.289 ns / 368.87 MHz | 14 s |
| Safe SystemVerilog | behavioral checks pass | N/A | 18 | 13 | 0 | 0 | 17.765 ns / 447.43 MHz | 15 s |
| Unsafe Anvil | compiler rejection expected | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| Safe Anvil generated SV | compiler acceptance expected | `-O 0` | not run | not run | not run | not run | not run | not run |
| Safe Anvil generated SV | compiler acceptance expected | `-O 1` | not run | not run | not run | not run | not run | not run |
| Safe Anvil generated SV | compiler acceptance expected | `-O 2` | not run | not run | not run | not run | not run | not run |

This is a code-generation and control-cost observation, not a language-wide
performance ranking. If the generated Anvil module does not have the same
external protocol and workload as the hand-written clients, report its numbers
separately rather than placing them in the same comparison table.

In this run the safe two-state client is smaller than the intentionally unsafe
three-state client. That reflects these two implementations; it is not evidence
that safety mechanisms generally reduce area or improve Fmax.

Quartus reports a restricted Fmax of 250 MHz for both rows. The larger values
in the table are raw internal-path estimates; they are retained as synthesis
details, not advertised as usable board clocks.

## Supported claims

After the artifacts have been produced, the experiment can support narrowly
worded observations such as:

- the naive SystemVerilog client passed latency one but failed a documented
  longer-latency execution;
- the safe SystemVerilog client passed every enumerated schedule and its monitor
  did not fire in those executions;
- the pinned Anvil compiler rejected the unsafe fixture and accepted the safe
  fixture; and
- the listed variants produced the recorded FPGA reports under one documented
  tool, device, constraint, and revision.

It does **not** establish that:

- a finite SystemVerilog simulation proves the design correct;
- Anvil proves functional correctness, liveness, deadlock freedom, CDC safety,
  or physical timing closure;
- the two language implementations are formally equivalent;
- Anvil has zero area, power, or frequency cost; or
- one result predicts all designs, tools, devices, or optimization levels.

## 90-second demonstration

**0--15 seconds — question.** Show the request-to-response interval and state
the rule: the address is borrowed until the dynamic response event, not for a
fixed number of cycles.

**15--35 seconds — counterexample.** Run or open the naive SystemVerilog trace.
Point out that latency one passes, then stop on the first longer-latency cycle
where the address changes while `outstanding` remains asserted. Show the
scoreboard or monitor failure.

**35--50 seconds — RTL repair.** Switch to the safe client. Identify the
captured outstanding address and show that it remains stable until response.
Report the finite latency grid and completed transaction count.

**50--70 seconds — static check.** Run the Anvil manifest harness or show its
saved log. Contrast rejection of
`mutate_while_loaned.anvil` with acceptance of
`dynamic_memory_client.anvil`; name the borrowed-register diagnostic rather
than presenting the compiler as a general verifier.

**70--85 seconds — evidence table.** Show the result record with revisions,
commands, artifacts, and checksums. If Quartus has been run, show the small
same-device table without claiming a universal area or frequency result.

**85--90 seconds — boundary.** Conclude that the example moves one
latency-dependent stability obligation from a test-specific observation into an
Anvil interface/type-checking obligation, while leaving functional verification
and hardware implementation as separate tasks.
