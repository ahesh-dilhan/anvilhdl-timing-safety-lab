"""Exhaustive bounded safety checks for timing scenarios."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

from .model import (
    EventInterval,
    IntervalResolutionError,
    ResolvedInterval,
    Scenario,
    Schedule,
)


@dataclass(frozen=True, slots=True)
class Violation:
    """A failed safety obligation and one concrete schedule witness."""

    kind: str
    check_id: tuple[str, ...]
    message: str
    schedule_index: int
    schedule: Schedule
    details: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "check": list(self.check_id),
            "message": self.message,
            "schedule_index": self.schedule_index,
            "schedule": self.schedule.to_dict(),
            "details": self.details,
        }


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Complete bounded analysis of one scenario."""

    scenario: Scenario
    schedules: tuple[Schedule, ...]
    violations: tuple[Violation, ...]

    @property
    def safe(self) -> bool:
        return not self.violations

    @property
    def schedules_checked(self) -> int:
        return len(self.schedules)

    @property
    def failing_schedule_count(self) -> int:
        return len({violation.schedule_index for violation in self.violations})

    @property
    def expectation_matches(self) -> bool | None:
        expected = self.scenario.expected_safe
        return None if expected is None else expected == self.safe

    def to_dict(self, include_schedules: bool = False) -> dict[str, object]:
        result: dict[str, object] = {
            "scenario": self.scenario.name,
            "description": self.scenario.description,
            "safe": self.safe,
            "expected_safe": self.scenario.expected_safe,
            "expectation_matches": self.expectation_matches,
            "schedules_checked": self.schedules_checked,
            "failing_schedules": self.failing_schedule_count,
            "violations": [violation.to_dict() for violation in self.violations],
        }
        if include_schedules:
            result["schedules"] = [schedule.to_dict() for schedule in self.schedules]
        return result


def _group_by(items: Iterable[object], attribute: str) -> dict[str, list[object]]:
    grouped: dict[str, list[object]] = defaultdict(list)
    for item in items:
        grouped[getattr(item, attribute)].append(item)
    return dict(grouped)


class TimingSafetyOracle:
    """Enumerate schedules and check the three modeled safety properties.

    This is an intentionally small teaching and diagnostics model. It
    is not the Anvil compiler, its type checker, or an implementation of the
    paper's formal semantics.
    """

    def __init__(self, max_schedules: int = 10_000) -> None:
        self.max_schedules = max_schedules

    def analyze(self, scenario: Scenario) -> AnalysisResult:
        schedules = tuple(
            scenario.dag.enumerate_schedules(max_schedules=self.max_schedules)
        )
        violations: list[Violation] = []
        lifetimes = {item.resource: item for item in scenario.lifetimes}
        loans_by_register = _group_by(scenario.loans, "register")
        mutations_by_register = _group_by(scenario.mutations, "register")
        promises_by_message = _group_by(scenario.promises, "message")

        for schedule_index, schedule in enumerate(schedules, start=1):
            resolved: dict[tuple[str, str], ResolvedInterval | None] = {}

            def resolve(
                category: str, name: str, interval: EventInterval
            ) -> ResolvedInterval | None:
                key = (category, name)
                if key in resolved:
                    return resolved[key]
                try:
                    value = interval.resolve(schedule)
                except IntervalResolutionError as exc:
                    value = None
                    violations.append(
                        Violation(
                            kind="invalid_interval",
                            check_id=("interval", category, name),
                            message=f"{category} '{name}' has an invalid interval: {exc}",
                            schedule_index=schedule_index,
                            schedule=schedule,
                            details={"category": category, "item": name},
                        )
                    )
                resolved[key] = value
                return value

            # Resolve every declared interval, even when no pairwise rule refers
            # to it. A reversed interval is itself an unsafe timing model.
            for item in scenario.lifetimes:
                resolve("lifetime", item.name, item.interval)
            for item in scenario.uses:
                resolve("use", item.name, item.interval)
            for item in scenario.loans:
                resolve("loan", item.name, item.interval)
            for item in scenario.mutations:
                resolve("mutation", item.name, item.interval)
            for item in scenario.promises:
                resolve("promise", item.name, item.interval)

            # A use must lie wholly inside its resource lifetime.
            for use in scenario.uses:
                lifetime = lifetimes[use.resource]
                use_interval = resolve("use", use.name, use.interval)
                lifetime_interval = resolve(
                    "lifetime", lifetime.name, lifetime.interval
                )
                if (
                    use_interval is not None
                    and lifetime_interval is not None
                    and not lifetime_interval.contains(use_interval)
                ):
                    violations.append(
                        Violation(
                            kind="lifetime_containment",
                            check_id=("lifetime", use.name),
                            message=(
                                f"use '{use.name}' {use_interval} escapes "
                                f"lifetime '{lifetime.name}' {lifetime_interval} "
                                f"for resource "
                                f"'{use.resource}'"
                            ),
                            schedule_index=schedule_index,
                            schedule=schedule,
                            details={
                                "resource": use.resource,
                                "use": use.name,
                                "use_interval": use_interval.to_list(),
                                "lifetime": lifetime.name,
                                "lifetime_interval": lifetime_interval.to_list(),
                            },
                        )
                    )

            # A register may not mutate while any loan of it is active.
            for register in sorted(set(loans_by_register) & set(mutations_by_register)):
                for loan in loans_by_register[register]:
                    loan_interval = resolve("loan", loan.name, loan.interval)
                    for mutation in mutations_by_register[register]:
                        mutation_interval = resolve(
                            "mutation", mutation.name, mutation.interval
                        )
                        if (
                            loan_interval is not None
                            and mutation_interval is not None
                            and loan_interval.overlaps(mutation_interval)
                        ):
                            violations.append(
                                Violation(
                                    kind="register_mutation_loan",
                                    check_id=("register", loan.name, mutation.name),
                                    message=(
                                        f"mutation '{mutation.name}' "
                                        f"{mutation_interval} overlaps loan "
                                        f"'{loan.name}' {loan_interval} of "
                                        f"register '{register}'"
                                    ),
                                    schedule_index=schedule_index,
                                    schedule=schedule,
                                    details={
                                        "register": register,
                                        "loan": loan.name,
                                        "loan_interval": loan_interval.to_list(),
                                        "mutation": mutation.name,
                                        "mutation_interval": mutation_interval.to_list(),
                                    },
                                )
                            )

            # A send's source must stay live until its promise is discharged.
            for promise in scenario.promises:
                if promise.resource is None:
                    continue
                lifetime = lifetimes[promise.resource]
                promise_interval = resolve("promise", promise.name, promise.interval)
                lifetime_interval = resolve(
                    "lifetime", lifetime.name, lifetime.interval
                )
                if (
                    promise_interval is not None
                    and lifetime_interval is not None
                    and not lifetime_interval.contains(promise_interval)
                ):
                    violations.append(
                        Violation(
                            kind="message_source_lifetime",
                            check_id=("promise-source", promise.name),
                            message=(
                                f"promise '{promise.name}' {promise_interval} "
                                f"outlives source "
                                f"resource '{promise.resource}' lifetime "
                                f"'{lifetime.name}' {lifetime_interval}"
                            ),
                            schedule_index=schedule_index,
                            schedule=schedule,
                            details={
                                "promise": promise.name,
                                "promise_interval": promise_interval.to_list(),
                                "resource": promise.resource,
                                "lifetime": lifetime.name,
                                "lifetime_interval": lifetime_interval.to_list(),
                            },
                        )
                    )

            # Repeated sends of one message specifier must not make overlapping
            # promises. Different messages on the same channel are independent.
            for message, promises in sorted(promises_by_message.items()):
                for first, second in combinations(promises, 2):
                    first_interval = resolve("promise", first.name, first.interval)
                    second_interval = resolve("promise", second.name, second.interval)
                    if (
                        first_interval is not None
                        and second_interval is not None
                        and first_interval.overlaps(second_interval)
                    ):
                        violations.append(
                            Violation(
                                kind="message_promise_overlap",
                                check_id=("promise", first.name, second.name),
                                message=(
                                    f"promise '{first.name}' {first_interval} "
                                    f"overlaps promise '{second.name}' "
                                    f"{second_interval} on "
                                    f"message '{message}'"
                                ),
                                schedule_index=schedule_index,
                                schedule=schedule,
                                details={
                                    "message": message,
                                    "first_promise": first.name,
                                    "first_interval": first_interval.to_list(),
                                    "second_promise": second.name,
                                    "second_interval": second_interval.to_list(),
                                },
                            )
                        )

        return AnalysisResult(
            scenario=scenario,
            schedules=schedules,
            violations=tuple(violations),
        )


def analyze(scenario: Scenario, max_schedules: int = 10_000) -> AnalysisResult:
    """Convenience wrapper around :class:`TimingSafetyOracle`."""

    return TimingSafetyOracle(max_schedules=max_schedules).analyze(scenario)
