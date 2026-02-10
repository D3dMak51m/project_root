from datetime import datetime
from uuid import uuid5, NAMESPACE_DNS
from typing import Dict, Any

from src.core.domain.commitment import ExecutionCommitment
from src.core.domain.execution_intent import ExecutionIntent
from src.core.domain.execution_binding import ExecutionBindingSnapshot


class ExecutionBindingService:
    """
    Pure service. Projects an internal ExecutionCommitment into an external ExecutionIntent.
    Strictly projection-only: copies values from commitment and snapshot.
    """

    def bind(
            self,
            commitment: ExecutionCommitment,
            snapshot: ExecutionBindingSnapshot,
            now: datetime
    ) -> ExecutionIntent:
        # 1. Deterministic ID Generation
        intent_id = uuid5(NAMESPACE_DNS, str(commitment.id))

        # 2. Constraints Projection (Direct Mapping)
        constraints: Dict[str, Any] = {
            "energy_budget": snapshot.energy_value,
            "timeout_seconds": 30
        }

        # 3. Reversibility Projection (Fixed Rule)
        reversible = False

        return ExecutionIntent(
            id=intent_id,
            commitment_id=commitment.id,
            intention_id=commitment.intention_id,
            persona_id=commitment.persona_id,
            abstract_action=commitment.abstract_action,  # Direct copy
            constraints=constraints,
            created_at=now,
            reversible=reversible,
            risk_level=commitment.risk_level  # Direct copy
        )