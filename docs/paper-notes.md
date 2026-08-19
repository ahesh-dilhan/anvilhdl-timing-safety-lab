# Technical reading notes

Paper: Jason Zhijingcheng Yu, Aditya Ranjan Jha, Umang Mathur, Trevor E.
Carlson, and Prateek Saxena, **“Anvil: A General-Purpose Timing-Safe Hardware
Description Language,”** arXiv:2503.19447v2, 27 October 2025. Page references
below use the printed paper pages in the 26-page PDF.

## One-sentence thesis

Anvil keeps explicit registers and cycle-level RTL control while using
event-parametric interface contracts and a static type system to rule out uses
of unstable, expired, or not-yet-meaningful signal values—even when a module's
latency varies at runtime.

## The problem is temporal ownership, not ordinary setup/hold timing

A register stores a persistent value. A signal derived from it is stateless and
changes when that register changes. Conventional HDL types describe bit widths
and structures but usually do not state that a consumer needs a particular
signal to remain unchanged for several cycles.

In the motivating memory example, the client assumes a one-cycle response,
changes its address, and reads an output while a two-cycle memory is still
processing the previous request. This causes both an early read and mutation of
a value still in use (Sections 1–2.1, pp. 1–3). The paper calls this class a
*timing hazard*. It is distinct from physical static timing analysis, although
both use the word “timing.”

## Why existing approaches leave a gap

- SystemVerilog, VHDL, Chisel, and SpinalHDL expose low-level control but do not
  make multi-cycle signal stability an interface type.
- Assertions and formal verification can express much more general properties,
  but the designer must write and maintain implementation-specific assertions.
  Checking may require cross-module state and can encounter state explosion.
- Bluespec rules prevent conflicting atomic actions within one cycle, but the
  scheduler does not encode an obligation that spans arbitrary later cycles.
- HLS languages largely avoid this hazard by presenting persistent,
  software-like values, at the cost of hiding register placement and detailed
  cycle control.
- Filament's timeline types preserve cycle control and provide timing safety,
  but their intervals have statically fixed lengths. A cache hit/miss or a page
  table walk needs an event-relative, dynamically sized interval.

These comparisons are developed in Sections 2.2–2.4 (pp. 3–4) and Section 8
(p. 13).

## Language model

### Processes and channels

An Anvil component is a `proc`. Processes communicate only through
bidirectional channels with `left` and `right` endpoints. Sending and receiving
are blocking rendezvous operations, similar to unbuffered Go/CSP channels
(Sections 3 and 4.1, pp. 5–6).

A channel message specifies three related but separate ideas:

1. direction and payload type;
2. a lifetime/expiry contract for the payload;
3. a synchronization mode for each endpoint.

The default `@dyn` synchronization mode uses runtime handshaking. A static mode
such as `@#2` requires readiness within at most two cycles of the preceding
receive. A dependent mode such as `@#wr_req+1` encodes an exact one-cycle
relation to the earlier message event.

### Concurrency and time

- `t1 >> t2`: wait for `t1` to complete, then start `t2`.
- `t1; t2`: initiate both terms concurrently.
- `cycle N`: complete after exactly `N` cycles.
- `loop { t }`: start the next iteration after `t` completes.
- `recursive { ... recurse ... }`: allow a later iteration to begin before the
  current one finishes, expressing pipelining.

Register assignment itself takes one cycle. These constructs expose time rather
than asking the compiler to invent a schedule (Sections 4.2–4.5, pp. 6–7).

## Abstract events make dynamic latency statically discussable

An event denotes completion of a term. A cycle delay creates an event at a fixed
offset from its predecessor (its absolute cycle can still be dynamic); a channel
rendezvous creates a dynamic event whose exact runtime cycle is unknown. The
compiler can still know causal and order relationships between those events.

An event pattern `e ▷ p` denotes the first event after `e` matching duration
`p`; `p` can be `#N` or a future channel operation. A set of patterns denotes
their earliest event (Section 5.1, pp. 7–8).

The compiler organizes events and timing edges into a DAG called the **event
graph**. Substituting concrete nonnegative delays for dynamic operations yields
a concrete runtime schedule; the graph represents the family of legal
schedules (Section 5.3, p. 8).

## Lifetime and loan time

A value lifetime is a half-open interval `[start, end)` in which the value is
meaningful and unchanged. Constants have an eternal end. An expression's
lifetime is constrained by its operands, effectively taking their intersection.

A register's loan time is a union of intervals in which values derived from
that register are still live or promised to another process. Mutating the
register during one of those intervals would change the associated stateless
signal, so the mutation is rejected (Section 5.2, p. 8).

The hardware analogy to borrowing is useful but incomplete: a loan is not only
lexically scoped. It can end at a runtime event such as the next response.

## The three safety obligations

For an event graph `G`, the paper defines an order relation `a ≤G b`: `a`
occurs no later than `b` under every legal concrete timing assignment. Interval
containment follows from ordering both endpoints. The implementation uses sound
approximations for these queries, so it may conservatively reject some safe
programs (Section 5.4, pp. 8–10; Appendix C.3, pp. 20–22).

The checker enforces:

1. **Valid value use:** every use window is contained in the value lifetime.
2. **Valid register mutation:** an assignment window is disjoint from every
   loan interval of that register.
3. **Valid message send:** the source value lives for the interval promised by
   the channel contract, and promises from repeated sends of the same message
   do not overlap.

The formal semantics represents each clock cycle as a set of `ValCreate`,
`ValUse`, `RegMut`, `ValSend`, and `ValRecv` actions. Composition aligns matching
sends and receives; dynamic transfers may be delayed by any nonnegative number
of cycles. Theorem C.20 states that every well-typed abstract Anvil program is
safe for all such execution logs (Appendix C, pp. 18–24).

That theorem is intentionally narrower than “the hardware is correct.” It does
not establish functional correctness, progress/deadlock freedom, CDC safety,
absence of combinational loops, information-flow security, or physical timing
closure.

## Compiler and lowering

The prototype is written in OCaml and emits synthesizable SystemVerilog. The
event graph is its central IR from parsing through type checking and lowering
(Section 6, pp. 10–11).

The paper describes four event-graph optimizations:

1. merge children reached by identical outbound delay labels;
2. remove an unbalanced join when one predecessor is provably later;
3. move a common branch-tail delay after the join;
4. merge a zero-delay branch join into its common predecessor.

Each process becomes an SV module. A message becomes up to three ports: data,
valid, and acknowledgement. Static or dependent synchronization knowledge can
remove the corresponding handshake port. Control flow becomes an FSM derived
from the event graph; state is needed for joins, cycle counters, and dynamic
handshakes.

Lifetimes and loans are erased after checking. There is no runtime lifetime
monitor, although the generated FSM/handshake structure can still affect area,
power, and critical path.

## Evaluation: what was actually measured

Ten designs cover common cells, dynamic-latency MMU blocks, AES, AXI-Lite
routers, and static pipelines. Every row has zero additional **clock-cycle**
latency; the paper explicitly distinguishes this from propagation delay
(Section 7 and Table 1, pp. 11–13).

| Comparison | Mean area | Mean power | Extra cycles |
| --- | ---: | ---: | ---: |
| Anvil vs handwritten SystemVerilog (8 designs) | +4.50% | +3.75% | 0 |
| Anvil vs Filament (2 designs) | −11.0% | +6.5% | 0 |

Notable individual results include PTW and AXI mux area at +12%, AES power at
+22%, and maximum frequency moving in both directions across designs. The
experiments use a commercial 22-nm ASIC process. Functional evidence consists
of unit tests or baseline smoke tests, rather than exhaustive equivalence.

The prose on p. 13 rounds the SystemVerilog power mean to 3.5%, while the
abstract and Table 1 report 3.75%. In discussion, the table value is the safer
number to quote.

## Constructive limitations and follow-up questions

- How often do the sound order approximations reject programs that are in fact
  safe, and which graph shapes dominate those false positives?
- How do graph size and type-check time scale with deeply pipelined or highly
  concurrent designs? Compiler runtime is not reported.
- How is correspondence between the full concrete implementation and the
  reduced formal core regression-tested?
- What contract annotation or wrapper design gives external SystemVerilog more
  precision than the conservative one-cycle lifetime described in Appendix B?
- Can graph rewrites be differential-tested against a bounded execution-log
  oracle while separately proving their symbolic correctness?
- How do place-and-route, FPGA mapping, complete subsystems, and developer
  effort change the practicality picture?

These are extensions of an explicitly early-stage prototype, not objections to
the central safety result.

## Glossary

| Term | Working definition |
| --- | --- |
| Timing safety | No out-of-lifetime use, mutation-under-loan, or invalid message promise in any execution. |
| Timing contract | Interface-level payload lifetime plus endpoint synchronization requirements. |
| Dynamic event | A named time point tied to runtime interaction rather than a fixed cycle. |
| Event pattern | The first fixed-delay or message-operation match after an event. |
| Event graph | DAG IR encoding causal and timing relationships among events. |
| Lifetime | Half-open interval in which a value is stable and meaningful. |
| Loan time | Intervals during which a register must not change because live values depend on it. |
| Safe composition | Independently well-typed processes sharing a channel contract cannot introduce the defined hazard. |
| Zero latency overhead | No extra clock cycles; not a claim of zero area, power, or critical-path cost. |
