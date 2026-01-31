from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any


class Environment(Enum):
    DEV = "DEV"
    TEST = "TEST"
    PROD = "PROD"
    REPLAY = "REPLAY"


@dataclass(frozen=True)
class SafetyLimits:
    max_ticks: int = 1000
    max_budget_delta_per_tick: float = 50.0
    max_events_per_tick: int = 10
    max_execution_time_ms: int = 5000


@dataclass(frozen=True)
class RuntimeProfile:
    """
    Configuration profile for the runtime environment.
    Controls safety limits, failure handling, and observability verbosity.
    Does NOT affect strategic logic.
    """
    env: Environment
    limits: SafetyLimits

    # Behavior flags
    fail_fast: bool = True
    enforce_invariants: bool = True
    enable_telemetry: bool = True
    allow_execution: bool = True

    @classmethod
    def dev(cls) -> 'RuntimeProfile':
        return cls(
            env=Environment.DEV,
            limits=SafetyLimits(max_ticks=100, max_budget_delta_per_tick=100.0),
            fail_fast=True,
            enforce_invariants=True,
            enable_telemetry=True,
            allow_execution=True
        )

    @classmethod
    def test(cls) -> 'RuntimeProfile':
        return cls(
            env=Environment.TEST,
            limits=SafetyLimits(max_ticks=50, max_budget_delta_per_tick=200.0),
            fail_fast=True,
            enforce_invariants=True,
            enable_telemetry=False,
            allow_execution=False  # Often mocked
        )

    @classmethod
    def prod(cls) -> 'RuntimeProfile':
        return cls(
            env=Environment.PROD,
            limits=SafetyLimits(max_ticks=1000000, max_budget_delta_per_tick=50.0),
            fail_fast=False,  # Prefer fail-soft with telemetry
            enforce_invariants=True,
            enable_telemetry=True,
            allow_execution=True
        )

    @classmethod
    def replay(cls) -> 'RuntimeProfile':
        return cls(
            env=Environment.REPLAY,
            limits=SafetyLimits(max_ticks=1000000, max_budget_delta_per_tick=1000.0),
            fail_fast=True,  # Replay must be strict
            enforce_invariants=True,
            enable_telemetry=True,  # Tagged as replay
            allow_execution=False  # STRICTLY FORBIDDEN
        )