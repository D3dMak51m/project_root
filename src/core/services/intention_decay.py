from datetime import datetime
from typing import Optional
from src.core.domain.intention import Intention
from src.core.domain.behavior import BehaviorState
from src.core.domain.readiness import ActionReadiness


class IntentionDecayService:
    """
    Pure service. Calculates the decay of an intention over time.
    Determines if an intention should persist or expire.
    """

    def evaluate(
            self,
            intention: Intention,
            state: BehaviorState,
            readiness: ActionReadiness,
            total_intentions: int,
            now: datetime,
            external_decay_factor: float = 1.0  # [NEW] External modulation
    ) -> Optional[Intention]:
        """
        Returns the updated Intention if it survives, or None if it expires.
        """

        # 1. Hard Expiration (Explicit calculation)
        age_seconds = (now - intention.created_at).total_seconds()
        if age_seconds > intention.ttl_seconds:
            return None

        # 2. Calculate Decay Factor
        decay_factor = 1.0

        # Low readiness accelerates decay
        if readiness.value < 20.0:
            decay_factor *= 2.0
        elif readiness.value < 50.0:
            decay_factor *= 1.5

        # High fatigue accelerates decay
        if state.fatigue > 70.0:
            decay_factor *= 1.5

        # Crowding penalty (more intentions = faster decay for weak ones)
        if total_intentions > 3:
            decay_factor *= 1.2

        # Apply external modulation (e.g. from execution feedback)
        decay_factor *= external_decay_factor

        # 3. Apply Decay to Priority (Smooth float decay)
        # Base decay rate per tick
        priority_decrement = 0.1 * decay_factor

        new_priority = intention.priority - priority_decrement

        if new_priority < 1.0:
            return None

        # 4. Return Updated Intention
        updated_intention = Intention(
            id=intention.id,
            type=intention.type,
            content=intention.content,
            priority=new_priority,
            created_at=intention.created_at,
            ttl_seconds=intention.ttl_seconds,
            metadata=intention.metadata
        )

        return updated_intention