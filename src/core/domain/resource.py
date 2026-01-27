from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Optional


@dataclass
class StrategicResourceBudget:
    """
    Global resource budget for the entire agent.
    Owned by the Orchestrator, not individual contexts.
    """
    energy_budget: float
    attention_budget: float
    execution_slots: int
    last_updated: datetime

    # Recovery rates (per hour)
    energy_recovery_rate: float = 10.0
    attention_recovery_rate: float = 20.0
    slot_recovery_rate: float = 1.0  # Slots recover slower


@dataclass(frozen=True)
class ResourceCost:
    """
    Estimated cost of executing an intent.
    """
    energy_cost: float
    attention_cost: float
    execution_slot_cost: int = 1


class AllocationStatus(Enum):
    APPROVED = "APPROVED"
    INSUFFICIENT_ENERGY = "INSUFFICIENT_ENERGY"
    INSUFFICIENT_ATTENTION = "INSUFFICIENT_ATTENTION"
    NO_SLOTS = "NO_SLOTS"


@dataclass(frozen=True)
class ResourceAllocationResult:
    """
    Result of a resource allocation request.
    """
    status: AllocationStatus
    approved: bool
    reserved_cost: Optional['ResourceCost'] = None