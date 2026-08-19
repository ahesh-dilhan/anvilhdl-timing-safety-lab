# Research discussion guide

This page organizes a technical discussion of Anvil. Start from the problem,
explain one mechanism precisely, and then distinguish the result from its
boundaries.

## A 90-second explanation

> Anvil addresses a gap between ordinary RTL and high-level synthesis. In RTL,
> a wire derived from a register changes whenever that register changes, but an
> interface usually cannot state how long the receiver needs that value to stay
> stable. That creates timing hazards such as changing a memory address while a
> variable-latency memory is still using it.
>
> Anvil makes the stability requirement part of a channel contract. Its key
> abstraction is an event: a fixed cycle can be an event, but so can the runtime
> rendezvous where a response arrives. A value can therefore have a lifetime
> like “from request until response” even though the number of cycles is unknown.
> The compiler builds an event DAG, infers value lifetimes and register loan
> times, and checks value uses, register mutations, and message sends.
>
> This retains explicit registers and cycle control, unlike HLS, while handling
> dynamic timing that static timeline types cannot express. The compiler erases
> the safety reasoning, lowers processes and channels to SystemVerilog modules,
> handshakes, and FSMs, and the evaluation reports zero additional clock cycles
> with modest average area and power overhead. The theorem is timing safety—not
> functional correctness or deadlock freedom.

## Core discussion questions

### What exactly is a timing hazard here?

A value is used outside the interval where its signal is meaningful and stable.
Typical causes are consuming output before readiness or mutating a backing
register while a downstream component still depends on the derived signal.

### Why are ready/valid and assertions not enough?

They can implement and verify a protocol, but conventional HDL types do not
carry the multi-cycle stability promise. The designer must implement it and
write implementation-specific assertions, often reasoning across modules.
Anvil checks one channel contract compositionally and generates the required
synchronization structure.

### How can a static checker handle an unknown response time?

It does not need the absolute cycle. It gives request and response completions
event identities, then proves causal/order facts that hold for every legal
concrete delay. The interval `[request, response)` is dynamically sized at
runtime but symbolically named at compile time.

### Lifetime versus loan time?

A lifetime says when a value is stable and meaningful. A loan time says when a
register may not be mutated because one or more live values depend on it. A
register can have a union of loan intervals.

### The exact three checks?

Every use fits inside its value lifetime; every register write is disjoint from
loan time; every sent source covers the message contract's promised lifetime,
and repeated promises for the same message do not overlap.

### `>>` versus `;`?

`>>` waits for the left term's completion event before starting the right term.
`;` initiates both terms concurrently. Because a send or receive can complete
dynamically, `>>` is also an event-relative timing operator.

### Anvil versus Filament, Bluespec, and HLS?

Filament has cycle/register control and timing types, but fixed static
timelines. Bluespec schedules non-conflicting atomic rules per cycle, not
multi-cycle value obligations. HLS gives persistent software-like values by
hiding much of register and cycle placement. Anvil aims to combine RTL control
with static, dynamic-event timing contracts.

### What happens in generated hardware?

A process becomes an SV module; channel messages become data plus only the
valid/ack signals their synchronization modes require; and the event graph
becomes FSM/control logic. Lifetime and loan metadata do not exist at runtime.

### Strongest evidence and cost?

Across ten evaluated components, no design gained a clock cycle. Against eight
SystemVerilog baselines, mean area is +4.50% and mean power +3.75%; individual
costs include +12% area and +22% power. Frequency improves in some rows and
declines in others. This is good prototype evidence, not a claim of zero cost.

### What does the theorem not prove?

It does not prove the algorithm, liveness/deadlock freedom, CDC behavior,
physical setup/hold closure, or general security. It proves the paper's value
lifetime, register mutation, and message-duration safety for well-typed
programs.

## Questions for Anvil maintainers

Select two or three based on the technical context rather than treating them as
a checklist.

1. The formal order relation is implemented with sound approximations. In
   current designs, which event-graph patterns create the most conservative
   rejections, and are better diagnostics or a stronger solver a priority?
2. Since the event graph is both the proof-facing model and the lowering IR,
   what invariants have been hardest to preserve across optimization passes?
3. How do you currently differential-test optimized event graphs and generated
   SystemVerilog? Would a small bounded execution-log oracle be useful as a
   second implementation?
4. Appendix B gives external RTL values a conservative one-cycle lifetime. What
   interface-annotation design do you see as the best path for richer,
   trustworthy SystemVerilog interoperability?
5. Which infrastructure problem is currently limiting contributors most:
   compiler diagnostics, regression-test latency, synthesis reproducibility,
   editor tooling, or larger benchmark integration?
6. The safety theorem is intentionally silent about liveness. Have real designs
   exposed a need for deadlock diagnostics while composing blocking channels?
7. What kind of external contribution would be most useful to the project: a
   narrowly proved compiler change, a well-tested infrastructure improvement,
   or a new benchmark with a reproducible evaluation?

## Constructive observations to mention carefully

- “Zero latency overhead” means clock cycles, not propagation delay. Table 1
  shows both frequency gains and regressions.
- The power average is printed as 3.75% in the abstract/Table 1 and rounded to
  3.5% in the Section 7.3 summary.
- Sound but incomplete graph-order reasoning invites a useful measurement of
  conservative rejection rates.
- Blocking channels make safety composition clean, while liveness remains a
  separate research problem.
- Ten blocks on one 22-nm flow are encouraging evidence; a scaling study,
  complete subsystem, FPGA/P&R result, or developer study would add a different
  kind of evidence.

These observations are best framed as research questions, not as attempts to
“catch” the authors.

## Repository summary

> I built a small, dependency-free bounded oracle for the paper's three safety
> obligations. It enumerates concrete dynamic-latency schedules from an event
> DAG and reports the first counterexample. It is deliberately not presented as
> the Anvil checker—the compiler proves an unbounded symbolic property. I see the
> oracle as an explanatory tool and a possible differential-testing seed for
> diagnostics and graph optimizations.

A useful live exercise is to open `experiments/02_early_address_mutation.json`,
change the response latency bound, and explain why a single passing schedule
does not establish safety.
