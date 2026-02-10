import random
from datetime import datetime
from typing import Optional

from src.core.domain.intention import Intention
from src.core.domain.persona import PersonaMask
from src.core.domain.behavior import BehaviorState
from src.core.domain.readiness import ActionReadiness
from src.core.domain.reputation import ReputationProfile
from src.core.domain.execution import ExecutionEligibilityResult


class ExecutionEligibilityService:
    """
    Pure service. Evaluates whether an Intention may proceed toward execution
    through a specific PersonaMask.
    """

    def evaluate(
            self,
            intention: Intention,
            mask: PersonaMask,
            state: BehaviorState,
            readiness: ActionReadiness,
            reputation: Optional[ReputationProfile],
            now: datetime
    ) -> ExecutionEligibilityResult:

        # 1. Fatigue & Energy Safety Check
        # If too tired, deny immediately to preserve resources.
        if state.fatigue > 80.0:
            return ExecutionEligibilityResult(
                allow=False,
                reason="Fatigue too high",
                risk_blocked=False
            )

        if state.energy < 20.0:
            return ExecutionEligibilityResult(
                allow=False,
                reason="Energy too low",
                risk_blocked=False
            )

        # 2. Persona Risk Tolerance Check
        # Intention priority acts as a proxy for "intensity/risk" here.
        # If priority is very high (e.g. 9-10), it might exceed mask tolerance.
        # (Simplified logic: priority/10 vs risk_tolerance)
        implied_risk = intention.priority / 10.0
        if implied_risk > mask.risk_tolerance:
            return ExecutionEligibilityResult(
                allow=False,
                reason="Risk exceeds mask tolerance",
                risk_blocked=True
            )

        # 3. Persona Activity Rate (Probability Gate)
        # Even if safe, the persona might just not act due to its nature.
        # Deterministic check for simulation (using hash or similar would be better for pure func,
        # but random is allowed in gates per architecture if controlled).
        # We use a simple threshold check against a random value.
        if random.random() > mask.activity_rate:
            return ExecutionEligibilityResult(
                allow=False,
                reason="Activity rate gate",
                risk_blocked=False
            )

        # 4. Global Silence Bias
        # Final probabilistic filter to ensure silence is default.
        if random.random() < 0.5:
            return ExecutionEligibilityResult(
                allow=False,
                reason="Global silence bias",
                risk_blocked=False
            )

        # 5. Allow
        return ExecutionEligibilityResult(
            allow=True,
            reason="Eligible for execution",
            risk_blocked=False
        )