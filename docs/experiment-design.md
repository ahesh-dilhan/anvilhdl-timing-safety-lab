# Experiment design

## Research question

Can a small concrete-schedule model make Anvil's three timing-safety obligations
observable, falsifiable, and useful for diagnostics without pretending to
replace the compiler's symbolic proof?

## Model

An experiment contains:

- a directed acyclic event graph;
- edges with either fixed nonnegative latency or a named bounded dynamic delay;
- half-open intervals whose endpoints are event-plus-offset expressions;
- containment, disjointness, or non-overlap obligations.

For every combination of dynamic delays within the declared finite bounds, the
lab computes an event schedule. An event occurs at the maximum of its incoming
predecessor arrival times, matching fork/join timing intuition. The checker then
evaluates all obligations on the resulting integer-cycle intervals.

This deliberately models only a clean subset of the paper's event semantics.
It does not model branching reachability, earliest-of event-pattern sets,
unbounded message delay, complete Anvil syntax, or composition/hiding.

## Hypotheses

| ID | Scenario | Expected observation |
| --- | --- | --- |
| H1 | `safe_dynamic_cache` | Mutating the address at the response boundary is disjoint from `[request, response)` for every explored latency. |
| H2 | `early_address_mutation` | The one-cycle-latency schedule can pass, but latency ≥2 yields a mutation-under-loan counterexample. |
| H3 | `premature_output_read` | A read scheduled from a fixed request-relative assumption escapes a response-relative lifetime for slower responses. |
| H4 | `overlapping_send` | A second promise that begins before the first expires violates message non-overlap. |

Regression tests check both each scenario's declared outcome and the exact
dynamic-delay values at its counterexample boundary.

## Why half-open intervals matter

The paper uses `[start, end)`. Therefore a mutation beginning exactly at the
loan's end is disjoint and safe. Treating both ends as closed would create a
false violation at the response boundary.

## Evidence levels

| Result | Meaning |
| --- | --- |
| `UNSAFE` with a counterexample | A concrete schedule in the declared model violates an obligation. |
| `BOUNDED SAFE` | Every enumerated schedule within the declared bounds satisfies the obligations. |
| Official Anvil type-check pass | The pinned compiler accepted the Anvil source under its implemented rules. |
| Paper theorem | Every well-typed program in the formal model is timing-safe for all executions. |

These levels must not be collapsed. In particular, bounded-safe is not proof.

## Potential infrastructure use

The model could evolve into a differential-testing oracle:

1. generate small bounded event DAGs and obligations;
2. obtain the oracle's concrete counterexamples;
3. translate the same cases to Anvil source;
4. compare compiler acceptance and normalized diagnostic categories;
5. minimize disagreements before classifying them as model gaps, conservative
   compiler rejections, or compiler bugs.

Any such claim would require a documented translation and much broader tests;
this repository currently provides only the first step.
