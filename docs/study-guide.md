# Two-day study guide

The objective is not to memorize the paper. It is to be able to explain one
example precisely, navigate the public implementation, and discuss a useful
next experiment with appropriate research caution.

## Day 1 — build the mental model

### Session 1: motivating failure (45 minutes)

1. Read Sections 1–3 of the paper.
2. Run `make demo`.
3. Open `experiments/02_early_address_mutation.json`.
4. Explain why latency 1 is safe in the bounded trace but latency 2 is not.
5. Change the mutation boundary and predict the result before rerunning it.

Success criterion: explain the Fig. 1 bug without saying only “handshake issue.”
Name the early read and mutation-under-loan as separate failures.

### Session 2: type-system mechanism (75 minutes)

1. Read Sections 4–5 and Appendix C.2–C.4.
2. Draw request and response as abstract events.
3. Write the three safety obligations from memory.
4. Explain why half-open `[start, end)` intervals make mutation at the exact
   response boundary legal.
5. Contrast the bounded oracle with Anvil's symbolic `≤G` reasoning.

Success criterion: answer “how can static typing handle unknown latency?” in
under one minute.

### Session 3: compiler path (60 minutes)

Read Section 6, then browse these files at the pinned upstream revision:

- `lib/lifetimeCheck.ml` — lifetime containment, loans, message checks;
- `lib/graphAnalysis.ml` — event-order analysis;
- `lib/eventGraph.ml` and related passes — core IR;
- `bin/main.ml` and `lib/config.ml` — driver and JSON interface;
- code-generation modules that lower events/processes to SystemVerilog.

Trace one negative fixture from source, through the expected checker category,
to JSON diagnostics.

Success criterion: describe which information is erased and which becomes
ports/FSM state.

## Day 2 — practice research discussion

### Session 4: evidence and boundaries (45 minutes)

1. Study Table 1 and Section 7.
2. Remember the defensible headline: 10 components, zero added clock cycles,
   +4.50% mean SV area, +3.75% mean SV power.
3. Note that frequency moves both ways and that the theorem is not functional
   correctness or liveness.
4. Review the limitations in `docs/paper-notes.md`.

Success criterion: discuss results without saying “zero overhead.”

### Session 5: repository walkthrough (60 minutes)

Practice a five-minute walkthrough:

1. README scope statement;
2. safe dynamic-cache scenario;
3. early-mutation counterexample;
4. one unit test;
5. official-compiler manifest and why it parses JSON `success`;
6. one possible next experiment.

Do not present planned Anvil/RTL integration as already reproduced. Say exactly
what was run locally and what is pinned for CI.

### Session 6: mock questions (45 minutes)

Use `docs/research-discussion-guide.md`. Answer aloud, then shorten each answer.
Prepare two questions for the maintainers that follow naturally from the
discussion.

Recommended pair:

- Which event-graph invariants are hardest to preserve across optimization?
- What infrastructure bottleneck would make a short external contribution
  immediately useful?

## Before a live discussion

- `make test` is green.
- GitHub Actions status and the exact upstream pin are known.
- The 90-second explanation is natural, not memorized word for word.
- One result, one limitation, and one proposed experiment are ready.
- The paper and a local copy of the repository are open.
- Questions focus on their current priorities rather than demonstrating trivia.

## If implementation work follows

Start with a one-page design note: objective, observable behavior, invariants,
tests, and non-goals. Pin dependencies, make negative tests explicit, keep
commits reviewable, and report failed approaches honestly. For compiler work,
prefer a minimal regression that fails before the change and passes after it;
for infrastructure work, make exit status and machine-readable output reliable
enough for CI consumers.
