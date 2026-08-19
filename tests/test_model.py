from __future__ import annotations

import unittest

from anvil_lab.model import (
    DelayRange,
    Event,
    EventDAG,
    EventInterval,
    EventPoint,
    IntervalResolutionError,
    ModelError,
    ResolvedInterval,
    Schedule,
    ScheduleLimitExceeded,
)


class DelayRangeTests(unittest.TestCase):
    def test_fixed_delay_has_one_choice(self) -> None:
        delay = DelayRange.fixed(2)
        self.assertTrue(delay.is_fixed)
        self.assertEqual(list(delay.choices()), [2])
        self.assertEqual(delay.choice_count, 1)

    def test_dynamic_delay_is_inclusive(self) -> None:
        delay = DelayRange(1, 3)
        self.assertFalse(delay.is_fixed)
        self.assertEqual(list(delay.choices()), [1, 2, 3])

    def test_invalid_delay_bounds_are_rejected(self) -> None:
        with self.assertRaises(ModelError):
            DelayRange(-1, 1)
        with self.assertRaises(ModelError):
            DelayRange(3, 2)
        with self.assertRaises(ModelError):
            DelayRange(True, 2)


class EventDAGTests(unittest.TestCase):
    def test_unknown_dependency_is_rejected(self) -> None:
        with self.assertRaisesRegex(ModelError, "unknown dependency"):
            EventDAG((Event("child", ("missing",)),))

    def test_cycle_is_rejected(self) -> None:
        with self.assertRaisesRegex(ModelError, "cycle"):
            EventDAG((Event("a", ("b",)), Event("b", ("a",))))

    def test_duplicate_event_is_rejected(self) -> None:
        with self.assertRaisesRegex(ModelError, "duplicate event"):
            EventDAG((Event("tick"), Event("tick")))

    def test_topological_order_handles_forward_declarations(self) -> None:
        dag = EventDAG(
            (
                Event("finish", ("start",), DelayRange.fixed(1)),
                Event("start", (), DelayRange.fixed(0)),
            )
        )
        self.assertEqual([event.name for event in dag.topological_order()], ["start", "finish"])

    def test_enumeration_covers_all_dynamic_choices(self) -> None:
        dag = EventDAG(
            (
                Event("start", delay=DelayRange.fixed(0)),
                Event("a", ("start",), DelayRange(1, 2)),
                Event("b", ("a",), DelayRange(0, 1)),
            )
        )
        schedules = list(dag.enumerate_schedules())
        self.assertEqual(dag.schedule_count, 4)
        self.assertEqual(len(schedules), 4)
        self.assertEqual(
            [(schedule.times["a"], schedule.times["b"]) for schedule in schedules],
            [(1, 1), (1, 2), (2, 2), (2, 3)],
        )

    def test_join_is_delayed_from_latest_predecessor(self) -> None:
        dag = EventDAG(
            (
                Event("root"),
                Event("short", ("root",), DelayRange.fixed(1)),
                Event("long", ("root",), DelayRange.fixed(4)),
                Event("join", ("short", "long"), DelayRange.fixed(2)),
            )
        )
        schedule = next(iter(dag.enumerate_schedules()))
        self.assertEqual(schedule.times["join"], 6)

    def test_schedule_limit_is_checked_before_enumeration(self) -> None:
        dag = EventDAG((Event("dynamic", delay=DelayRange(0, 5)),))
        with self.assertRaises(ScheduleLimitExceeded):
            list(dag.enumerate_schedules(max_schedules=5))

    def test_schedule_limit_must_be_positive_integer(self) -> None:
        dag = EventDAG((Event("tick"),))
        with self.assertRaises(ModelError):
            list(dag.enumerate_schedules(max_schedules=0))


class IntervalTests(unittest.TestCase):
    def test_touching_half_open_intervals_do_not_overlap(self) -> None:
        first = ResolvedInterval(1, 3)
        second = ResolvedInterval(3, 5)
        self.assertFalse(first.overlaps(second))

    def test_shared_cycle_overlaps(self) -> None:
        self.assertTrue(ResolvedInterval(1, 4).overlaps(ResolvedInterval(3, 5)))

    def test_empty_interval_does_not_overlap(self) -> None:
        self.assertFalse(ResolvedInterval(2, 2).overlaps(ResolvedInterval(1, 3)))

    def test_containment_accepts_shared_boundaries(self) -> None:
        outer = ResolvedInterval(1, 5)
        self.assertTrue(outer.contains(ResolvedInterval(1, 5)))
        self.assertTrue(outer.contains(ResolvedInterval(2, 5)))
        self.assertFalse(outer.contains(ResolvedInterval(0, 2)))

    def test_event_relative_offsets_resolve(self) -> None:
        schedule = Schedule(times={"start": 2, "finish": 7}, delays={})
        interval = EventInterval(EventPoint("start", 1), EventPoint("finish", -1))
        self.assertEqual(interval.resolve(schedule), ResolvedInterval(3, 6))

    def test_reversed_interval_is_rejected_per_schedule(self) -> None:
        schedule = Schedule(times={"later": 4, "earlier": 1}, delays={})
        interval = EventInterval(EventPoint("later"), EventPoint("earlier"))
        with self.assertRaises(IntervalResolutionError):
            interval.resolve(schedule)


if __name__ == "__main__":
    unittest.main()
