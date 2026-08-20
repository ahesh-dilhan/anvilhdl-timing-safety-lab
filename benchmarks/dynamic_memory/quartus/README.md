# Quartus structural comparison

This directory provides a noninteractive, reproducible synthesis flow for the
safe and intentionally unsafe dynamic-memory clients. It is pinned to the same
settings for every variant:

- Quartus Prime Lite 21.1;
- Cyclone IV E `EP4CE115F29C7`;
- 20 ns (`50 MHz`) clock named `dynamic_memory_clk` on top-level port `clk`;
- fitter seed `1`; and
- two Quartus worker processes.

The target matches the Cyclone IV device already used by a project in this
workspace. No board pin assignments are required because this is a structural
area/timing comparison, not a programming image or timing-signoff flow.

## Run one variant

Pass only synthesizable RTL. Do not pass the testbench or the variable-latency
memory model.

```bash
benchmarks/dynamic_memory/quartus/run_variant.sh \
  unsafe unsafe_dynamic_memory_client \
  benchmarks/dynamic_memory/rtl/unsafe_dynamic_memory_client.sv

benchmarks/dynamic_memory/quartus/run_variant.sh \
  safe safe_dynamic_memory_client \
  benchmarks/dynamic_memory/rtl/safe_dynamic_memory_client.sv
```

The equivalent direct command is:

```bash
quartus_sh -t benchmarks/dynamic_memory/quartus/run.tcl \
  --variant safe \
  --top safe_dynamic_memory_client \
  --rtl benchmarks/dynamic_memory/rtl/safe_dynamic_memory_client.sv
```

Each compilation is written to the ignored directory
`benchmarks/dynamic_memory/quartus/build/VARIANT/`.

## Collect comparable metrics

After compiling two variants:

```bash
python3 benchmarks/dynamic_memory/quartus/collect_results.py \
  benchmarks/dynamic_memory/quartus/build/unsafe \
  benchmarks/dynamic_memory/quartus/build/safe \
  --output benchmarks/dynamic_memory/quartus/build/results.csv
```

The CSV records logic elements, combinational functions, registers, memory
bits, 9-bit multiplier elements, slow-corner setup slack, raw path Fmax,
device-restricted Fmax, tool/device identity, and elapsed flow time.

The checked-in run is [`measured_results.csv`](measured_results.csv). On
Quartus 21.1 it measured 22 logic elements and 15 registers for the unsafe
three-state client versus 18 logic elements and 13 registers for the safe
two-state client. This is a result for these two tiny implementations, not a
general claim that safe designs are always smaller.

Quartus restricts both reported Fmax values to 250 MHz for this device. The raw
368.87/447.43 MHz path estimates remain in the CSV for transparency and must
not be described as achievable board clocks.

The comparison is deliberately labelled **structural**. Synthesizing the
unsafe client tells us its implementation cost; it does not make its protocol
behavior correct. Also, the SDC constrains internal register-to-register paths
only, so these numbers must not be presented as board timing sign-off.
