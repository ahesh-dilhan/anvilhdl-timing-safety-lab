"""JSON scenario loader with contextual validation errors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, TypeVar

from .model import (
    DelayRange,
    Event,
    EventDAG,
    EventInterval,
    EventPoint,
    Lifetime,
    Loan,
    MessagePromise,
    ModelError,
    Mutation,
    Scenario,
    Use,
)


class ScenarioFormatError(ValueError):
    """Raised when a JSON scenario does not match the supported schema."""


T = TypeVar("T")


def _object(value: object, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ScenarioFormatError(f"{context} must be a JSON object")
    return value


def _array(value: object, context: str) -> list[object]:
    if not isinstance(value, list):
        raise ScenarioFormatError(f"{context} must be a JSON array")
    return value


def _string(value: object, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ScenarioFormatError(f"{context} must be a non-empty string")
    return value


def _integer(value: object, context: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ScenarioFormatError(f"{context} must be an integer")
    return value


def _required(data: dict[str, Any], key: str, context: str) -> object:
    try:
        return data[key]
    except KeyError as exc:
        raise ScenarioFormatError(f"{context} is missing required field '{key}'") from exc


def _reject_unknown(
    data: dict[str, Any], allowed: set[str], context: str
) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        noun = "field" if len(unknown) == 1 else "fields"
        rendered = ", ".join(repr(key) for key in unknown)
        raise ScenarioFormatError(f"{context} has unknown {noun}: {rendered}")


def _delay(value: object, context: str) -> DelayRange:
    if isinstance(value, int) and not isinstance(value, bool):
        return DelayRange.fixed(value)
    data = _object(value, context)
    if "fixed" in data:
        _reject_unknown(data, {"fixed"}, context)
        cycles = _integer(data["fixed"], f"{context}.fixed")
        return DelayRange.fixed(cycles)
    _reject_unknown(data, {"min", "max"}, context)
    minimum = _integer(_required(data, "min", context), f"{context}.min")
    maximum = _integer(_required(data, "max", context), f"{context}.max")
    return DelayRange(minimum, maximum)


def _event(value: object, index: int) -> Event:
    context = f"events[{index}]"
    data = _object(value, context)
    _reject_unknown(data, {"id", "after", "delay"}, context)
    name = _string(_required(data, "id", context), f"{context}.id")
    raw_after = data.get("after", [])
    after = tuple(
        _string(item, f"{context}.after[{item_index}]")
        for item_index, item in enumerate(_array(raw_after, f"{context}.after"))
    )
    delay = _delay(data.get("delay", 0), f"{context}.delay")
    return Event(name=name, after=after, delay=delay)


def _point(value: object, context: str) -> EventPoint:
    if isinstance(value, str):
        return EventPoint(value)
    data = _object(value, context)
    _reject_unknown(data, {"event", "offset"}, context)
    event = _string(_required(data, "event", context), f"{context}.event")
    offset = _integer(data.get("offset", 0), f"{context}.offset")
    return EventPoint(event=event, offset=offset)


def _interval(value: object, context: str) -> EventInterval:
    data = _object(value, context)
    _reject_unknown(data, {"start", "end"}, context)
    return EventInterval(
        start=_point(_required(data, "start", context), f"{context}.start"),
        end=_point(_required(data, "end", context), f"{context}.end"),
    )


def _timed_item(
    value: object,
    index: int,
    section: str,
    grouping_field: str,
    constructor: Callable[..., T],
) -> T:
    context = f"{section}[{index}]"
    data = _object(value, context)
    _reject_unknown(data, {"id", grouping_field, "interval"}, context)
    name = _string(_required(data, "id", context), f"{context}.id")
    grouping = _string(
        _required(data, grouping_field, context), f"{context}.{grouping_field}"
    )
    interval = _interval(_required(data, "interval", context), f"{context}.interval")
    return constructor(name=name, **{grouping_field: grouping}, interval=interval)


def _items(
    root: dict[str, Any],
    section: str,
    grouping_field: str,
    constructor: Callable[..., T],
) -> tuple[T, ...]:
    values = _array(root.get(section, []), section)
    return tuple(
        _timed_item(value, index, section, grouping_field, constructor)
        for index, value in enumerate(values)
    )


def _promises(root: dict[str, Any]) -> tuple[MessagePromise, ...]:
    values = _array(root.get("promises", []), "promises")
    promises: list[MessagePromise] = []
    for index, value in enumerate(values):
        context = f"promises[{index}]"
        data = _object(value, context)
        _reject_unknown(data, {"id", "message", "interval", "resource"}, context)
        resource_value = data.get("resource")
        resource = (
            None
            if resource_value is None
            else _string(resource_value, f"{context}.resource")
        )
        promises.append(
            MessagePromise(
                name=_string(_required(data, "id", context), f"{context}.id"),
                message=_string(
                    _required(data, "message", context), f"{context}.message"
                ),
                interval=_interval(
                    _required(data, "interval", context), f"{context}.interval"
                ),
                resource=resource,
            )
        )
    return tuple(promises)


def scenario_from_dict(value: object) -> Scenario:
    """Parse and validate a scenario from already-decoded JSON data."""

    root = _object(value, "scenario")
    _reject_unknown(
        root,
        {
            "name",
            "description",
            "expected",
            "events",
            "lifetimes",
            "uses",
            "loans",
            "mutations",
            "promises",
        },
        "scenario",
    )
    name = _string(_required(root, "name", "scenario"), "scenario.name")
    description_value = root.get("description", "")
    if not isinstance(description_value, str):
        raise ScenarioFormatError("scenario.description must be a string")

    event_values = _array(_required(root, "events", "scenario"), "events")
    try:
        events = tuple(_event(item, index) for index, item in enumerate(event_values))
    except ModelError as exc:
        raise ScenarioFormatError(f"invalid scenario '{name}': {exc}") from exc

    expected_value = root.get("expected")
    if expected_value is None:
        expected_safe = None
    elif isinstance(expected_value, bool):
        expected_safe = expected_value
    elif expected_value in ("safe", "unsafe"):
        expected_safe = expected_value == "safe"
    else:
        raise ScenarioFormatError(
            "scenario.expected must be 'safe', 'unsafe', true, false, or absent"
        )

    try:
        return Scenario(
            name=name,
            description=description_value,
            dag=EventDAG(events),
            lifetimes=_items(root, "lifetimes", "resource", Lifetime),
            uses=_items(root, "uses", "resource", Use),
            loans=_items(root, "loans", "register", Loan),
            mutations=_items(root, "mutations", "register", Mutation),
            promises=_promises(root),
            expected_safe=expected_safe,
        )
    except ModelError as exc:
        raise ScenarioFormatError(f"invalid scenario '{name}': {exc}") from exc


def load_scenario(path: str | Path) -> Scenario:
    """Load one UTF-8 JSON scenario from ``path``."""

    source = Path(path)
    try:
        with source.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ScenarioFormatError(
            f"{source}: invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    except OSError as exc:
        raise ScenarioFormatError(f"cannot read {source}: {exc}") from exc

    try:
        return scenario_from_dict(data)
    except ScenarioFormatError as exc:
        if str(exc).startswith(f"{source}:"):
            raise
        raise ScenarioFormatError(f"{source}: {exc}") from exc
