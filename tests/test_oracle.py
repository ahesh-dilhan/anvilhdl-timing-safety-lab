from __future__ import annotations

import unittest

from anvil_lab.model import (
    DelayRange,
    Event,
    EventDAG,
    EventInterval,
    EventPoint,
    Lifetime,
    Loan,
    MessagePromise,
    Mutation,
    Scenario,
    Use,
)
from anvil_lab.oracle import analyze


def interval(start: str, end: str, *, end_offset: int = 0) -> EventInterval:
    return EventInterval(EventPoint(start), EventPoint(end, end_offset))


def basic_dag() -> EventDAG:
    return EventDAG(
        (
            Event("start"),
            Event("middle", ("start",), DelayRange.fixed(2)),
            Event("end", ("middle",), DelayRange.fixed(2)),
        )
    )


class OracleTests(unittest.TestCase):
    def test_lifetime_containment_safe(self) -> None:
        scenario = Scenario(
            "contained",
            "",
            basic_dag(),
            lifetimes=(Lifetime("life", "value", interval("start", "end")),),
            uses=(Use("sample", "value", interval("middle", "end")),),
        )
        self.assertTrue(analyze(scenario).safe)

    def test_lifetime_containment_reports_witness(self) -> None:
        scenario = Scenario(
            "escape",
            "",
            basic_dag(),
            lifetimes=(Lifetime("life", "value", interval("middle", "end")),),
            uses=(Use("sample", "value", interval("start", "middle")),),
        )
        result = analyze(scenario)
        self.assertFalse(result.safe)
        self.assertEqual(result.violations[0].kind, "lifetime_containment")
        self.assertEqual(result.violations[0].details["use_interval"], [0, 2])

    def test_mutation_at_loan_end_is_safe(self) -> None:
        scenario = Scenario(
            "boundary",
            "",
            basic_dag(),
            loans=(Loan("borrow", "reg", interval("start", "middle")),),
            mutations=(Mutation("write", "reg", interval("middle", "end")),),
        )
        self.assertTrue(analyze(scenario).safe)

    def test_mutation_during_loan_is_unsafe(self) -> None:
        scenario = Scenario(
            "mutation",
            "",
            basic_dag(),
            loans=(Loan("borrow", "reg", interval("start", "end")),),
            mutations=(Mutation("write", "reg", interval("middle", "end")),),
        )
        result = analyze(scenario)
        self.assertEqual(
            [violation.kind for violation in result.violations],
            ["register_mutation_loan"],
        )

    def test_mutation_of_different_register_is_safe(self) -> None:
        scenario = Scenario(
            "independent-registers",
            "",
            basic_dag(),
            loans=(Loan("borrow", "first", interval("start", "end")),),
            mutations=(Mutation("write", "second", interval("start", "end")),),
        )
        self.assertTrue(analyze(scenario).safe)

    def test_touching_message_promises_are_safe(self) -> None:
        scenario = Scenario(
            "serialized",
            "",
            basic_dag(),
            promises=(
                MessagePromise("first", "out", interval("start", "middle")),
                MessagePromise("second", "out", interval("middle", "end")),
            ),
        )
        self.assertTrue(analyze(scenario).safe)

    def test_overlapping_message_promises_are_unsafe(self) -> None:
        scenario = Scenario(
            "overlap",
            "",
            basic_dag(),
            promises=(
                MessagePromise("first", "out", interval("start", "end")),
                MessagePromise("second", "out", interval("middle", "end")),
            ),
        )
        result = analyze(scenario)
        self.assertEqual(result.violations[0].kind, "message_promise_overlap")

    def test_message_source_lifetime_covers_promise(self) -> None:
        scenario = Scenario(
            "source-live",
            "",
            basic_dag(),
            lifetimes=(Lifetime("life", "payload", interval("start", "end")),),
            promises=(
                MessagePromise(
                    "send", "out", interval("middle", "end"), resource="payload"
                ),
            ),
        )
        self.assertTrue(analyze(scenario).safe)

    def test_message_source_that_expires_during_promise_is_unsafe(self) -> None:
        scenario = Scenario(
            "source-expires",
            "",
            basic_dag(),
            lifetimes=(Lifetime("life", "payload", interval("start", "middle")),),
            promises=(
                MessagePromise(
                    "send", "out", interval("start", "end"), resource="payload"
                ),
            ),
        )
        result = analyze(scenario)
        self.assertEqual(len(result.violations), 1)
        self.assertEqual(result.violations[0].kind, "message_source_lifetime")
        self.assertEqual(result.violations[0].details["resource"], "payload")

    def test_promises_for_different_messages_are_independent(self) -> None:
        scenario = Scenario(
            "messages",
            "",
            basic_dag(),
            promises=(
                MessagePromise("first", "bus.req", interval("start", "end")),
                MessagePromise("second", "bus.res", interval("start", "end")),
            ),
        )
        self.assertTrue(analyze(scenario).safe)

    def test_structured_check_keys_cannot_collide_on_colons(self) -> None:
        scenario = Scenario(
            "collision-safe-keys",
            "",
            basic_dag(),
            loans=(
                Loan("a:b", "reg", interval("start", "end")),
                Loan("a", "reg", interval("start", "end")),
            ),
            mutations=(
                Mutation("c", "reg", interval("start", "end")),
                Mutation("b:c", "reg", interval("start", "end")),
            ),
        )
        result = analyze(scenario)
        self.assertEqual(len(result.violations), 4)
        self.assertEqual(len({item.check_id for item in result.violations}), 4)

    def test_invalid_interval_becomes_a_violation(self) -> None:
        scenario = Scenario(
            "invalid-runtime-interval",
            "",
            basic_dag(),
            promises=(
                MessagePromise("bad", "out", interval("end", "start")),
                MessagePromise("other", "out", interval("start", "middle")),
            ),
        )
        result = analyze(scenario)
        self.assertEqual(len(result.violations), 1)
        self.assertEqual(result.violations[0].kind, "invalid_interval")

    def test_dynamic_scenario_counts_only_failing_schedules(self) -> None:
        dag = EventDAG(
            (
                Event("start"),
                Event("loan_end", ("start",), DelayRange(1, 3)),
                Event("write", ("start",), DelayRange.fixed(1)),
            )
        )
        scenario = Scenario(
            "sometimes",
            "",
            dag,
            loans=(Loan("borrow", "reg", interval("start", "loan_end")),),
            mutations=(
                Mutation("write", "reg", interval("write", "write", end_offset=1)),
            ),
        )
        result = analyze(scenario)
        self.assertEqual(result.schedules_checked, 3)
        self.assertEqual(result.failing_schedule_count, 2)
        self.assertEqual(len(result.violations), 2)

    def test_expectation_matching(self) -> None:
        scenario = Scenario("expected", "", basic_dag(), expected_safe=True)
        result = analyze(scenario)
        self.assertTrue(result.expectation_matches)
        payload = result.to_dict(include_schedules=True)
        self.assertEqual(len(payload["schedules"]), 1)


if __name__ == "__main__":
    unittest.main()
