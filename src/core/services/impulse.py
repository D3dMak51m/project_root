from typing import List
from datetime import datetime
from src.core.context.internal import InternalContext
from src.core.domain.intention_candidate import IntentionCandidate


class ImpulseGenerator:
    """
    Pure service. Scans internal context for pressure concentrations.
    Emits candidates based on numeric thresholds only.
    """

    def generate(self, context: InternalContext, now: datetime) -> List[IntentionCandidate]:
        candidates = []

        # 1. Global Readiness Check
        # If overall readiness is low, no specific impulses can form.
        if context.readiness_value < 60.0:
            return []

        # 2. Stance-based Impulse Generation
        # (In a real implementation, we would iterate over stance topics in context.
        # For C.4 architecture, we simulate extraction from context signals)

        # Example logic: If a topic in recent thoughts has high pressure/intensity
        # This relies on context being populated correctly in C.2

        # Mocking extraction for architectural demonstration:
        # In production, InternalContext would carry structured Stance snapshots.
        # Here we assume if readiness is high, we emit a generic candidate for the dominant pressure.

        if context.readiness_value > 80.0:
            candidates.append(IntentionCandidate(
                topic="general_pressure",
                pressure=context.readiness_value,
                created_at=now
            ))

        return candidates