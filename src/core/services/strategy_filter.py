from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from src.core.domain.intention import Intention
from src.core.domain.strategy import StrategicPosture
from src.core.domain.readiness import ActionReadiness


@dataclass(frozen=True)
class StrategicFilterResult:
    allow: bool
    suppress: bool
    reason: str
    # defer and suggested_resume_after removed as Strategy no longer controls timing


class StrategicFilterService:
    """
    Pure service. Evaluates intentions against the current strategic posture.
    Acts as a cold SEMANTIC veto layer: suppresses or allows intentions based on policy and risk.
    Does NOT handle timing, deferral, or readiness thresholds.
    """

    def evaluate(
            self,
            intention: Intention,
            posture: StrategicPosture,
            # readiness argument removed - strategy does not check readiness physics
            now: datetime
    ) -> StrategicFilterResult:

        # 1. Engagement Policy Check (Semantic)
        # If the intention type is explicitly forbidden by policy, suppress.
        if any(policy in intention.type for policy in posture.engagement_policy):
            return StrategicFilterResult(
                allow=False,
                suppress=True,
                reason="Forbidden by engagement policy"
            )

        # 2. Risk Tolerance Check (Semantic)
        # If intention metadata implies risk higher than tolerance, suppress.
        # Assuming intention metadata might carry a 'risk_estimate' or similar.
        # If not present, we assume neutral risk.
        # This is a semantic check, not a readiness check.
        intention_risk = intention.metadata.get("risk_estimate", 0.0)
        if intention_risk > posture.risk_tolerance:
            return StrategicFilterResult(
                allow=False,
                suppress=True,
                reason="Risk estimate exceeds strategic tolerance"
            )

        # 3. Horizon Compatibility Check (Semantic)
        # If intention is short-term but strategy is long-horizon, we might suppress
        # to avoid noise. This is a semantic mismatch, not a timing delay.
        # Example: "impulse" origin might be too noisy for a 30-day horizon.
        if posture.horizon_days > 7 and intention.metadata.get("origin") == "impulse":
            return StrategicFilterResult(
                allow=False,
                suppress=True,
                reason="Impulse incompatible with long-term horizon"
            )

        # 4. Default: Allow
        return StrategicFilterResult(
            allow=True,
            suppress=False,
            reason="Strategic criteria met"
        )