from typing import List
from datetime import datetime
from src.memory.domain.counterfactual_event import CounterfactualEvent


class CounterfactualAnalyzer:
    """
    Pure service. Analyzes counterfactual events to detect systemic blocks and friction.
    """

    def analyze(self, events: List[CounterfactualEvent], now: datetime) -> dict:
        if not events:
            return {
                "missed_opportunity_pressure": 0.0,
                "governance_friction_index": 0.0,
                "policy_conflict_density": 0.0
            }

        # Filter recent events (e.g., last 100 ticks or time window)
        # For simplicity in M.5, we analyze the provided list (assumed scoped/recent)

        total_events = len(events)

        # 1. Governance Friction
        # Ratio of events blocked by Governance or Policy
        gov_blocks = sum(1 for e in events if e.suppression_stage in ("Governance", "Policy"))
        friction_index = gov_blocks / total_events if total_events > 0 else 0.0

        # 2. Policy Conflict Density
        # Specific focus on Policy rejections
        policy_blocks = sum(1 for e in events if e.suppression_stage == "Policy")
        conflict_density = policy_blocks / total_events if total_events > 0 else 0.0

        # 3. Missed Opportunity Pressure
        # Sum of risk/value of suppressed intents (if available)
        # We use risk_level as a proxy for "potential impact"
        opportunity_pressure = 0.0
        for e in events:
            if e.intent:
                # Higher risk often correlates with higher potential impact/change
                opportunity_pressure += e.intent.risk_level
            else:
                # If intent wasn't formed (e.g. suppressed early), assume baseline
                opportunity_pressure += 0.1

        # Normalize pressure (arbitrary scale, e.g., per 10 events)
        normalized_pressure = opportunity_pressure / max(1, total_events / 10)

        return {
            "missed_opportunity_pressure": normalized_pressure,
            "governance_friction_index": friction_index,
            "policy_conflict_density": conflict_density
        }