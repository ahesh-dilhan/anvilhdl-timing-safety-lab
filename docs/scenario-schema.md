# Scenario JSON schema

The lab intentionally uses a small human-editable JSON format. It is not Anvil
syntax and does not attempt to serialize the compiler's event graph.

## Minimal scenario

```json
{
  "name": "one_tick",
  "description": "One fixed event and no obligations.",
  "expected": "safe",
  "events": [
    {"id": "tick", "delay": 0}
  ]
}
```

`expected` may be `"safe"`, `"unsafe"`, `true`, `false`, or omitted. Use
`--fail-on-mismatch` in CI when expectations are present.

## Events

```json
{"id": "response", "after": ["request"], "delay": {"min": 1, "max": 4}}
```

- `id` is unique.
- `after` names zero or more predecessor events. The graph must be acyclic.
- `delay` is either a nonnegative integer, `{"fixed": N}`, or inclusive bounds
  `{"min": A, "max": B}`.
- A source occurs `delay` cycles after cycle zero. Any other event occurs
  `delay` cycles after its latest predecessor.

Every ranged event contributes choices to the Cartesian product. The default
CLI limit is 10,000 complete schedules.

## Event-relative intervals

An endpoint may be an event name:

```json
{"start": "request", "end": "response"}
```

or an event plus a signed offset:

```json
{
  "start": {"event": "response", "offset": 0},
  "end": {"event": "response", "offset": 1}
}
```

Intervals are half-open `[start, end)`. A resolved end before its start is an
`invalid_interval` violation.

## Lifetimes and uses

```json
"lifetimes": [
  {
    "id": "data_live",
    "resource": "data",
    "interval": {"start": "response", "end": "data_expire"}
  }
],
"uses": [
  {
    "id": "consume_data",
    "resource": "data",
    "interval": {"start": "consume", "end": "consume_done"}
  }
]
```

Each modeled resource has one lifetime. Every use must be fully contained in
that lifetime for every enumerated schedule.

## Register loans and mutations

```json
"loans": [
  {
    "id": "address_loan",
    "register": "address_reg",
    "interval": {"start": "request", "end": "response"}
  }
],
"mutations": [
  {
    "id": "advance_address",
    "register": "address_reg",
    "interval": {
      "start": "response",
      "end": {"event": "response", "offset": 1}
    }
  }
]
```

Every mutation must be disjoint from every loan on the same register. Touching
at the half-open boundary is safe.

## Message promises

```json
"promises": [
  {
    "id": "send_response",
    "message": "memory.response",
    "resource": "data",
    "interval": {"start": "send", "end": "send_done"}
  }
]
```

Promises created by repeated sends of the same message specifier (`pi.m`) must
be pairwise disjoint. Qualify the field as `channel.message` when useful;
different messages on one bidirectional channel are independent. If `resource`
is present, the corresponding lifetime must contain the entire promise. Omit
`resource` only when a scenario is focused on message reservation rather than
source-data coverage.

## Result vocabulary

| Violation kind | Meaning |
| --- | --- |
| `lifetime_containment` | A use escapes its resource lifetime. |
| `register_mutation_loan` | A mutation overlaps a loan of the same register. |
| `message_source_lifetime` | A promised send outlives its source value. |
| `message_promise_overlap` | Two sends of the same message make overlapping promises. |
| `invalid_interval` | An interval resolves with end before start. |

Use `--json --show-schedules` to obtain every delay assignment and event time
for downstream analysis.
