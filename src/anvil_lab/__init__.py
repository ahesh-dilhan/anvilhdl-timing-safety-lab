"""A bounded, pedagogical timing-safety oracle inspired by Anvil."""

from .loader import ScenarioFormatError, load_scenario, scenario_from_dict
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
    ResolvedInterval,
    Scenario,
    Schedule,
    ScheduleLimitExceeded,
    Use,
)
from .oracle import AnalysisResult, TimingSafetyOracle, Violation, analyze

__all__ = [
    "AnalysisResult",
    "DelayRange",
    "Event",
    "EventDAG",
    "EventInterval",
    "EventPoint",
    "Lifetime",
    "Loan",
    "MessagePromise",
    "ModelError",
    "Mutation",
    "ResolvedInterval",
    "Scenario",
    "ScenarioFormatError",
    "Schedule",
    "ScheduleLimitExceeded",
    "TimingSafetyOracle",
    "Use",
    "Violation",
    "analyze",
    "load_scenario",
    "scenario_from_dict",
]

__version__ = "0.1.0"
