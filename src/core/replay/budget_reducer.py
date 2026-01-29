from src.core.domain.resource import StrategicResourceBudget
from src.core.ledger.budget_event import BudgetEvent


class BudgetReplayReducer:
    """
    Pure service. Reconstructs budget state from events.
    Ensures determinism by applying deltas strictly.
    """

    def reduce(self, budget: StrategicResourceBudget, event: BudgetEvent) -> StrategicResourceBudget:
        delta = event.delta

        # Apply deltas
        new_energy = budget.energy_budget + delta.get("energy", 0.0)
        new_attention = budget.attention_budget + delta.get("attention", 0.0)
        new_slots = budget.execution_slots + int(delta.get("slots", 0))

        # Enforce bounds (same logic as ResourceManager, but purely applicative)
        # Recovery logic might cap at 100, reservation might drop below 0 (though shouldn't if validated)
        # We assume events are valid, but enforce caps for safety/consistency with domain rules.

        if event.event_type == "BUDGET_RECOVERED":
            new_energy = min(100.0, new_energy)
            new_attention = min(100.0, new_attention)
            new_slots = min(10, new_slots)

        return StrategicResourceBudget(
            energy_budget=new_energy,
            attention_budget=new_attention,
            execution_slots=new_slots,
            last_updated=event.timestamp,
            energy_recovery_rate=budget.energy_recovery_rate,
            attention_recovery_rate=budget.attention_recovery_rate,
            slot_recovery_rate=budget.slot_recovery_rate
        )