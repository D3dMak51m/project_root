from datetime import datetime
from typing import Optional, Dict
from src.core.domain.resource import StrategicResourceBudget, ResourceCost, ResourceAllocationResult, AllocationStatus
from src.core.domain.execution_intent import ExecutionIntent
from src.core.domain.exceptions import BudgetInvariantViolation


class StrategicResourceManager:
    """
    Pure service. Manages the global strategic resource budget.
    Handles evaluation, reservation, commitment, and recovery of resources.
    Enforces strict two-phase resource consumption: evaluate -> reserve -> commit/rollback.
    """

    def recover(self, budget: StrategicResourceBudget, now: datetime) -> StrategicResourceBudget:
        """
        Calculates resource recovery over time.
        """
        delta_hours = (now - budget.last_updated).total_seconds() / 3600.0
        if delta_hours <= 0:
            return budget

        new_energy = min(100.0, budget.energy_budget + (budget.energy_recovery_rate * delta_hours))
        new_attention = min(100.0, budget.attention_budget + (budget.attention_recovery_rate * delta_hours))
        new_slots = min(10, int(budget.execution_slots + (budget.slot_recovery_rate * delta_hours)))

        return StrategicResourceBudget(
            energy_budget=new_energy,
            attention_budget=new_attention,
            execution_slots=new_slots,
            last_updated=now,
            energy_recovery_rate=budget.energy_recovery_rate,
            attention_recovery_rate=budget.attention_recovery_rate,
            slot_recovery_rate=budget.slot_recovery_rate
        )

    def calculate_recovery_delta(self, budget: StrategicResourceBudget, now: datetime) -> Dict[str, float]:
        delta_hours = (now - budget.last_updated).total_seconds() / 3600.0
        if delta_hours <= 0:
            return {}

        energy_gain = budget.energy_recovery_rate * delta_hours
        attention_gain = budget.attention_recovery_rate * delta_hours
        slots_gain = int(budget.slot_recovery_rate * delta_hours)

        return {
            "energy": energy_gain,
            "attention": attention_gain,
            "slots": float(slots_gain)
        }

    def evaluate(self, intent: ExecutionIntent, budget: StrategicResourceBudget) -> ResourceAllocationResult:
        """
        Checks if the budget can afford the intent's cost.
        Does NOT mutate the budget.
        Strictly rejects intents without estimated cost.
        """
        cost = intent.estimated_cost
        if not cost:
            return ResourceAllocationResult(AllocationStatus.INSUFFICIENT_ATTENTION, False)

        if budget.execution_slots < cost.execution_slot_cost:
            return ResourceAllocationResult(AllocationStatus.NO_SLOTS, False)

        if budget.energy_budget < cost.energy_cost:
            return ResourceAllocationResult(AllocationStatus.INSUFFICIENT_ENERGY, False)

        if budget.attention_budget < cost.attention_cost:
            return ResourceAllocationResult(AllocationStatus.INSUFFICIENT_ATTENTION, False)

        return ResourceAllocationResult(AllocationStatus.APPROVED, True, reserved_cost=cost)

    def calculate_reservation_delta(self, cost: ResourceCost) -> Dict[str, float]:
        return {
            "energy": -cost.energy_cost,
            "attention": -cost.attention_cost,
            "slots": -float(cost.execution_slot_cost)
        }

    def reserve(self, budget: StrategicResourceBudget, cost: ResourceCost) -> StrategicResourceBudget:
        """
        Reserves resources from the budget.
        Returns a new budget instance with resources deducted.
        Enforces non-negative budget invariant strictly.
        """
        new_energy = budget.energy_budget - cost.energy_cost
        new_attention = budget.attention_budget - cost.attention_cost
        new_slots = budget.execution_slots - cost.execution_slot_cost

        # Invariant Check: Budget cannot be negative
        if new_energy < 0 or new_attention < 0 or new_slots < 0:
            raise BudgetInvariantViolation(
                f"Negative budget after reservation: energy={new_energy}, attention={new_attention}, slots={new_slots}"
            )

        return StrategicResourceBudget(
            energy_budget=new_energy,
            attention_budget=new_attention,
            execution_slots=new_slots,
            last_updated=budget.last_updated,
            energy_recovery_rate=budget.energy_recovery_rate,
            attention_recovery_rate=budget.attention_recovery_rate,
            slot_recovery_rate=budget.slot_recovery_rate
        )

    def commit(self, budget: StrategicResourceBudget) -> StrategicResourceBudget:
        return budget

    def rollback(self, budget: StrategicResourceBudget, cost: ResourceCost) -> StrategicResourceBudget:
        return StrategicResourceBudget(
            energy_budget=budget.energy_budget + cost.energy_cost,
            attention_budget=budget.attention_budget + cost.attention_cost,
            execution_slots=budget.execution_slots + cost.execution_slot_cost,
            last_updated=budget.last_updated,
            energy_recovery_rate=budget.energy_recovery_rate,
            attention_recovery_rate=budget.attention_recovery_rate,
            slot_recovery_rate=budget.slot_recovery_rate
        )