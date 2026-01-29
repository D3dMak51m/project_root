from datetime import datetime
from typing import Optional, Dict
from src.core.domain.resource import StrategicResourceBudget, ResourceCost, ResourceAllocationResult, AllocationStatus
from src.core.domain.execution_intent import ExecutionIntent


class StrategicResourceManager:
    """
    Pure service. Manages the global strategic resource budget.
    Calculates deltas for events, does NOT mutate budget directly.
    """

    def calculate_recovery_delta(self, budget: StrategicResourceBudget, now: datetime) -> Dict[str, float]:
        """
        Calculates potential recovery delta based on time passed.
        Returns delta dict, does not apply it.
        """
        delta_hours = (now - budget.last_updated).total_seconds() / 3600.0
        if delta_hours <= 0:
            return {}

        energy_gain = budget.energy_recovery_rate * delta_hours
        attention_gain = budget.attention_recovery_rate * delta_hours
        slots_gain = int(budget.slot_recovery_rate * delta_hours)

        # Cap gains to not exceed max (logic handled in reducer/application, but delta should reflect potential)
        # Actually, delta should be precise. If we are at 99 and gain 10, delta is 1?
        # No, standard event sourcing usually records the calculated delta or the target state.
        # To keep reducer pure and simple, we record the *calculated gain*.
        # The reducer applies min(100, current + gain).

        return {
            "energy": energy_gain,
            "attention": attention_gain,
            "slots": float(slots_gain)
        }

    def recover(self, budget: StrategicResourceBudget, now: datetime) -> StrategicResourceBudget:
        """
        Calculates resource recovery over time.
        """
        delta_hours = (now - budget.last_updated).total_seconds() / 3600.0
        if delta_hours <= 0:
            return budget

        new_energy = min(100.0, budget.energy_budget + (budget.energy_recovery_rate * delta_hours))
        new_attention = min(100.0, budget.attention_budget + (budget.attention_recovery_rate * delta_hours))
        # TODO: Implement fractional slot recovery or cooldown logic in E.8
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

    def reserve(self, budget: StrategicResourceBudget, cost: ResourceCost) -> StrategicResourceBudget:
        """
        Reserves resources from the budget.
        Returns a new budget instance with resources deducted.
        This is a temporary hold; must be followed by commit() or rollback().
        """
        return StrategicResourceBudget(
            energy_budget=budget.energy_budget - cost.energy_cost,
            attention_budget=budget.attention_budget - cost.attention_cost,
            execution_slots=budget.execution_slots - cost.execution_slot_cost,
            last_updated=budget.last_updated,
            energy_recovery_rate=budget.energy_recovery_rate,
            attention_recovery_rate=budget.attention_recovery_rate,
            slot_recovery_rate=budget.slot_recovery_rate
        )

    def commit(self, budget: StrategicResourceBudget) -> StrategicResourceBudget:
        """
        Finalizes resource consumption after successful execution.
        For E.7 this is a semantic no-op as reservation already deducted resources,
        but it marks the point of no return for resource accounting.
        Future stages might use this for logging or secondary effects.
        """
        return budget

    def rollback(self, budget: StrategicResourceBudget, cost: ResourceCost) -> StrategicResourceBudget:
        """
        Returns resources to the budget (e.g., if execution failed before consumption or was cancelled).
        """
        return StrategicResourceBudget(
            energy_budget=budget.energy_budget + cost.energy_cost,
            attention_budget=budget.attention_budget + cost.attention_cost,
            execution_slots=budget.execution_slots + cost.execution_slot_cost,
            last_updated=budget.last_updated,
            energy_recovery_rate=budget.energy_recovery_rate,
            attention_recovery_rate=budget.attention_recovery_rate,
            slot_recovery_rate=budget.slot_recovery_rate
        )

    def calculate_reservation_delta(self, cost: ResourceCost) -> Dict[str, float]:
        return {
            "energy": -cost.energy_cost,
            "attention": -cost.attention_cost,
            "slots": -float(cost.execution_slot_cost)
        }