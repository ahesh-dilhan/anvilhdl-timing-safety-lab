"""Core timing model used by the pedagogical safety oracle.

The model deliberately stays small: events form a DAG and each event occurs an
integer number of cycles after its latest predecessor.  A delay may be fixed or
range over a bounded set of integers.  Enumerating every delay choice gives the
bounded schedules inspected by :mod:`anvil_lab.oracle`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Iterable, Mapping


class ModelError(ValueError):
    """Raised when a timing model is malformed."""


class ScheduleLimitExceeded(ModelError):
    """Raised before enumeration when a model has too many schedules."""


class IntervalResolutionError(ModelError):
    """Raised when an event-relative interval is invalid in a schedule."""


def _is_int(value: object) -> bool:
    """Return true for integers while rejecting booleans."""

    return isinstance(value, int) and not isinstance(value, bool)


@dataclass(frozen=True, slots=True)
class DelayRange:
    """Inclusive, non-negative integer delay bounds in clock cycles."""

    minimum: int
    maximum: int

    def __post_init__(self) -> None:
        if not _is_int(self.minimum) or not _is_int(self.maximum):
            raise ModelError("delay bounds must be integers")
        if self.minimum < 0:
            raise ModelError("delay bounds cannot be negative")
        if self.maximum < self.minimum:
            raise ModelError("delay maximum must be at least the minimum")

    @classmethod
    def fixed(cls, cycles: int) -> "DelayRange":
        return cls(cycles, cycles)

    @property
    def is_fixed(self) -> bool:
        return self.minimum == self.maximum

    @property
    def choice_count(self) -> int:
        return self.maximum - self.minimum + 1

    def choices(self) -> range:
        return range(self.minimum, self.maximum + 1)


@dataclass(frozen=True, slots=True)
class Event:
    """An event delayed from the latest of zero or more predecessor events."""

    name: str
    after: tuple[str, ...] = ()
    delay: DelayRange = field(default_factory=lambda: DelayRange.fixed(0))

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ModelError("event names must be non-empty strings")
        if not isinstance(self.after, tuple) or not all(
            isinstance(parent, str) and parent for parent in self.after
        ):
            raise ModelError(f"event '{self.name}' dependencies must be event names")
        if len(set(self.after)) != len(self.after):
            raise ModelError(f"event '{self.name}' repeats a dependency")
        if self.name in self.after:
            raise ModelError(f"event '{self.name}' cannot depend on itself")
        if not isinstance(self.delay, DelayRange):
            raise ModelError(f"event '{self.name}' must have a DelayRange")


@dataclass(frozen=True, slots=True)
class Schedule:
    """One complete assignment of event times and selected delays."""

    times: Mapping[str, int]
    delays: Mapping[str, int]

    def to_dict(self) -> dict[str, dict[str, int]]:
        return {"times": dict(self.times), "delays": dict(self.delays)}


@dataclass(frozen=True, slots=True)
class EventDAG:
    """A validated event DAG with deterministic bounded schedule enumeration."""

    events: tuple[Event, ...]

    def __post_init__(self) -> None:
        if not self.events:
            raise ModelError("a scenario must define at least one event")
        names = [event.name for event in self.events]
        if len(set(names)) != len(names):
            duplicate = next(name for name in names if names.count(name) > 1)
            raise ModelError(f"duplicate event '{duplicate}'")
        known = set(names)
        for event in self.events:
            missing = [parent for parent in event.after if parent not in known]
            if missing:
                raise ModelError(
                    f"event '{event.name}' has unknown dependency '{missing[0]}'"
                )
        # Eagerly detect cycles so all EventDAG instances are valid.
        self.topological_order()

    def topological_order(self) -> tuple[Event, ...]:
        """Return a stable topological order, preserving declaration order."""

        by_name = {event.name: event for event in self.events}
        indegree = {event.name: len(event.after) for event in self.events}
        children: dict[str, list[str]] = {event.name: [] for event in self.events}
        for event in self.events:
            for parent in event.after:
                children[parent].append(event.name)

        ready = [event.name for event in self.events if indegree[event.name] == 0]
        ordered: list[Event] = []
        while ready:
            name = ready.pop(0)
            ordered.append(by_name[name])
            for child in children[name]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    # Re-sort by declaration order for deterministic output.
                    ready.append(child)
                    ready.sort(key=lambda item: list(by_name).index(item))

        if len(ordered) != len(self.events):
            cyclic = [name for name, degree in indegree.items() if degree]
            raise ModelError(f"event graph contains a cycle involving: {', '.join(cyclic)}")
        return tuple(ordered)

    @property
    def schedule_count(self) -> int:
        count = 1
        for event in self.events:
            count *= event.delay.choice_count
        return count

    def enumerate_schedules(self, max_schedules: int = 10_000) -> Iterable[Schedule]:
        """Yield schedules for every bounded delay assignment.

        An event with predecessors occurs ``selected_delay`` cycles after its
        latest predecessor. A source event is delayed from cycle zero.
        """

        if not _is_int(max_schedules) or max_schedules <= 0:
            raise ModelError("max_schedules must be a positive integer")
        count = self.schedule_count
        if count > max_schedules:
            raise ScheduleLimitExceeded(
                f"scenario has {count} schedules, above limit {max_schedules}"
            )

        ordered = self.topological_order()
        choices = [event.delay.choices() for event in ordered]
        for selected in product(*choices):
            times: dict[str, int] = {}
            delays: dict[str, int] = {}
            for event, delay in zip(ordered, selected, strict=True):
                baseline = max((times[parent] for parent in event.after), default=0)
                times[event.name] = baseline + delay
                delays[event.name] = delay
            yield Schedule(times=times, delays=delays)


@dataclass(frozen=True, slots=True)
class EventPoint:
    """A schedule point expressed as an event plus a signed cycle offset."""

    event: str
    offset: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.event, str) or not self.event:
            raise ModelError("an event point needs a non-empty event name")
        if not _is_int(self.offset):
            raise ModelError("an event point offset must be an integer")

    def resolve(self, schedule: Schedule) -> int:
        try:
            return schedule.times[self.event] + self.offset
        except KeyError as exc:
            raise IntervalResolutionError(
                f"interval refers to unknown event '{self.event}'"
            ) from exc


@dataclass(frozen=True, slots=True)
class ResolvedInterval:
    """A half-open interval ``[start, end)`` in clock cycles."""

    start: int
    end: int

    def __post_init__(self) -> None:
        if not _is_int(self.start) or not _is_int(self.end):
            raise IntervalResolutionError("resolved interval bounds must be integers")
        if self.end < self.start:
            raise IntervalResolutionError(
                f"interval end {self.end} precedes start {self.start}"
            )

    def overlaps(self, other: "ResolvedInterval") -> bool:
        """Return whether two half-open intervals share at least one cycle."""

        return max(self.start, other.start) < min(self.end, other.end)

    def contains(self, other: "ResolvedInterval") -> bool:
        """Return whether this interval fully contains ``other``."""

        return self.start <= other.start and other.end <= self.end

    def to_list(self) -> list[int]:
        return [self.start, self.end]

    def __str__(self) -> str:
        return f"[{self.start}, {self.end})"


@dataclass(frozen=True, slots=True)
class EventInterval:
    """A half-open interval whose endpoints are relative to DAG events."""

    start: EventPoint
    end: EventPoint

    def resolve(self, schedule: Schedule) -> ResolvedInterval:
        return ResolvedInterval(self.start.resolve(schedule), self.end.resolve(schedule))


@dataclass(frozen=True, slots=True)
class Lifetime:
    name: str
    resource: str
    interval: EventInterval


@dataclass(frozen=True, slots=True)
class Use:
    name: str
    resource: str
    interval: EventInterval


@dataclass(frozen=True, slots=True)
class Loan:
    name: str
    register: str
    interval: EventInterval


@dataclass(frozen=True, slots=True)
class Mutation:
    name: str
    register: str
    interval: EventInterval


@dataclass(frozen=True, slots=True)
class MessagePromise:
    name: str
    message: str
    interval: EventInterval
    resource: str | None = None


def _validate_named_items(items: tuple[object, ...], category: str) -> None:
    names: list[str] = []
    for item in items:
        name = getattr(item, "name", None)
        if not isinstance(name, str) or not name:
            raise ModelError(f"{category} names must be non-empty strings")
        names.append(name)
        interval = getattr(item, "interval", None)
        if not isinstance(interval, EventInterval):
            raise ModelError(f"{category} '{name}' needs an event-relative interval")
        grouping_field = {
            "lifetime": "resource",
            "use": "resource",
            "loan": "register",
            "mutation": "register",
            "promise": "message",
        }[category]
        grouping = getattr(item, grouping_field, None)
        if not isinstance(grouping, str) or not grouping:
            raise ModelError(
                f"{category} '{name}' {grouping_field} must be a non-empty string"
            )
    if len(names) != len(set(names)):
        duplicate = next(name for name in names if names.count(name) > 1)
        raise ModelError(f"duplicate {category} '{duplicate}'")


@dataclass(frozen=True, slots=True)
class Scenario:
    """A complete timing-safety scenario."""

    name: str
    description: str
    dag: EventDAG
    lifetimes: tuple[Lifetime, ...] = ()
    uses: tuple[Use, ...] = ()
    loans: tuple[Loan, ...] = ()
    mutations: tuple[Mutation, ...] = ()
    promises: tuple[MessagePromise, ...] = ()
    expected_safe: bool | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ModelError("scenario name must be a non-empty string")
        if not isinstance(self.description, str):
            raise ModelError("scenario description must be a string")
        if not isinstance(self.dag, EventDAG):
            raise ModelError("scenario requires an EventDAG")
        if self.expected_safe is not None and not isinstance(self.expected_safe, bool):
            raise ModelError("expected_safe must be true, false, or absent")

        categories = (
            (self.lifetimes, "lifetime"),
            (self.uses, "use"),
            (self.loans, "loan"),
            (self.mutations, "mutation"),
            (self.promises, "promise"),
        )
        for items, category in categories:
            _validate_named_items(items, category)

        lifetime_resources = [lifetime.resource for lifetime in self.lifetimes]
        if len(lifetime_resources) != len(set(lifetime_resources)):
            raise ModelError("each resource may have only one modeled lifetime")
        known_resources = set(lifetime_resources)
        for use in self.uses:
            if use.resource not in known_resources:
                raise ModelError(
                    f"use '{use.name}' refers to resource '{use.resource}' "
                    "without a lifetime"
                )
        for promise in self.promises:
            if promise.resource is not None:
                if not isinstance(promise.resource, str) or not promise.resource:
                    raise ModelError(
                        f"promise '{promise.name}' resource must be a non-empty string"
                    )
                if promise.resource not in known_resources:
                    raise ModelError(
                        f"promise '{promise.name}' refers to resource "
                        f"'{promise.resource}' without a lifetime"
                    )

        event_names = {event.name for event in self.dag.events}
        for items, category in categories:
            for item in items:
                interval = getattr(item, "interval")
                for point in (interval.start, interval.end):
                    if point.event not in event_names:
                        raise ModelError(
                            f"{category} '{getattr(item, 'name')}' refers to "
                            f"unknown event '{point.event}'"
                        )
