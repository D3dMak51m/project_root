import random
from datetime import datetime, timedelta
from typing import Optional

from src.core.domain.intention import Intention
from src.core.domain.persona import PersonaMask
from src.core.domain.behavior import BehaviorState
from src.core.domain.readiness import ActionReadiness
from src.core.domain.execution import ExecutionEligibilityResult
from src.core.domain.window import ExecutionWindow


class CommitmentEvaluator:
    """
    Pure service. Decides whether to open an ExecutionWindow for an eligible intention.
    Acts as a probabilistic gatekeeper to ensure action is rare.
    """

    def evaluate(
            self,
            intention: Intention,
            eligibility: ExecutionEligibilityResult,
            mask: PersonaMask,
            state: BehaviorState,
            readiness: ActionReadiness,
            now: datetime
    ) -> Optional[ExecutionWindow]:

        # 1. Hard Gate: Eligibility
        if not eligibility.allow:
            return None

        # 2. Readiness Check
        # Even if eligible, readiness must be substantial for commitment
        if readiness.value < 60.0:
            return None

        # 3. Fatigue Check
        # High fatigue reduces commitment probability drastically
        if state.fatigue > 60.0:
            return None

        # 4. Probabilistic Filter (The "Hesitation" Factor)
        # Base chance is low to ensure silence is default.
        # Factors increasing chance:
        # - High readiness
        # - High intention priority
        # - Low fatigue

        base_chance = 0.3
        readiness_bonus = (readiness.value - 60.0) / 200.0  # Max +0.2
        priority_bonus = (intention.priority / 20.0)  # Max +0.5 (if priority is 10)

        total_chance = base_chance + readiness_bonus + priority_bonus

        # Cap at 80% even in perfect conditions
        total_chance = min(0.8, total_chance)

        if random.random() > total_chance:
            return None

        # 5. Open Window
        # Window is short-lived (e.g., 5 seconds logical time)
        return ExecutionWindow(
            intention_id=intention.id,
            persona_id=mask.id,
            opened_at=now,
            expires_at=now + timedelta(seconds=5),
            confidence=total_chance,
            reason="Commitment threshold met"
        )