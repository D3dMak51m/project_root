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
        if context.readiness_value < 40.0:
            return []

        # 2. Stance-based Impulse Generation
        # Iterate over read-only stance snapshot from context
        for topic, intensity in context.stance_snapshot.items():

            # Calculate local pressure for this topic
            # Formula: Topic Intensity * Global Readiness Factor
            # Example: 0.8 intensity * (80 readiness / 100) = 0.64 local pressure

            readiness_factor = context.readiness_value / 100.0
            local_pressure = intensity * readiness_factor * 100.0

            # Threshold for impulse generation
            # Must be significant enough to warrant attention
            if local_pressure > 50.0:
                candidates.append(IntentionCandidate(
                    topic=topic,
                    pressure=local_pressure,
                    created_at=now
                ))

        return candidates