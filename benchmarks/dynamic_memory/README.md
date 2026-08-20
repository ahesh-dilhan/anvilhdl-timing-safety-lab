# Dynamic-memory RTL benchmark

This benchmark turns Anvil's motivating cross-cycle lifetime problem into a
small, self-checking SystemVerilog experiment.  Two clients receive the same
addresses and deterministic response latencies:

```text
addresses:  10 23 36 49 5c 6f (hex)
latencies:   1  2  3  4  1  4 (cycles)
```

The memory acknowledges a request before it finishes using the request address.
Its contract therefore borrows `req_addr` until `rsp_valid`.  The unsafe client
assumes this loan is always one cycle and changes the address too early.  The
safe client waits for the actual response event.

Run with Icarus Verilog 11 or newer from the repository root:

```bash
benchmarks/dynamic_memory/sim/run_iverilog.sh
```

`run_iverilog.sh` also accepts `IVERILOG`, `VVP`, and `IVERILOG_BASE`
environment overrides for a manually unpacked installation.  Alternatively,
run the installed Questa Intel Starter simulator:

```bash
benchmarks/dynamic_memory/sim/run_questa.sh
```

Questa 2021.2 compiles these sources without warnings, but that installation
requires a valid license environment to start `vsim`.  The script prints its
license preflight state and points to `LM_LICENSE_FILE` if checkout fails.
Set `QUESTA_BIN=/path/to/questa/bin` when Questa is installed somewhere other
than the default Intel FPGA directory below the current user's home directory.

The command exits successfully only when all of these expected observations
hold:

- both clients complete all six identical transactions on identical cycles;
- latency-one transactions pass for both clients;
- the unsafe client produces four stability violations and four data
  mismatches at the four longer latencies; and
- the safe client produces no stability violation or data mismatch.

Machine-readable-ish `RESULT` lines and the portable waveform are written below
`sim/generated/`.  Load `dynamic_memory.vcd` in GTKWave or another VCD viewer
and compare `unsafe_req_addr` with `unsafe_loan_address` while
`unsafe_outstanding` is high.

This is a deterministic simulation counterexample, not a proof of general RTL
correctness.  The corresponding Anvil distinction is exercised separately by
the compiler fixtures in `anvil/unsafe/mutate_while_loaned.anvil` and
`anvil/safe/dynamic_memory_client.anvil`.
