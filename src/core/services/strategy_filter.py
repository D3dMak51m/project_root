from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple
from src.core.domain.intention import Intention
from src.core.domain.strategy import StrategicPosture
from src.core.domain.strategic_memory import StrategicMemory
from src.core.domain.strategic_context import StrategicContext
from src.core.services.path_key import extract_path_key


@dataclass(frozen=True)
class StrategicFilterResult:
    allow: bool
    suppress: bool
    reason: str


class StrategicFilterService:
    """
    Pure service. Evaluates intentions against strategic posture and memory.
    Acts as a cold SEMANTIC veto layer.
    Memory-aware: checks for path abandonment and cooldowns.
    """

    def evaluate(
            self,
            intention: Intention,
            posture: StrategicPosture,
            memory: StrategicMemory,
            context: StrategicContext,
            now: datetime
    ) -> StrategicFilterResult:

        path_key = extract_path_key(intention, context)
        path_status = memory.get_status(path_key)

        # 1. Strategic Memory Check (Abandonment) - HARD GATE
        if path_status.abandonment_level == "hard":
            return StrategicFilterResult(
                allow=False,
                suppress=True,
                reason=f"Path {path_key} is hard-abandoned"
            )

        if path_status.abandonment_level == "soft":
            # Check cooldown expiration
            if path_status.cooldown_until and now < path_status.cooldown_until:
                return StrategicFilterResult(
                    allow=False,
                    suppress=True,
                    reason=f"Path {path_key} is soft-abandoned (cooldown active)"
                )
            # If cooldown expired or not set (shouldn't happen for soft), allow to proceed to policy checks
            # Implicitly: cooldown expired -> treat as normal

        # 2. Engagement Policy Check (Semantic)
        if any(policy in intention.type for policy in posture.engagement_policy):
            return StrategicFilterResult(
                allow=False,
                suppress=True,
                reason="Forbidden by engagement policy"
            )

        # 3. Risk Tolerance Check (Semantic)
        intention_risk = intention.metadata.get("risk_estimate", 0.0)
        if intention_risk > posture.risk_tolerance:
            return StrategicFilterResult(
                allow=False,
                suppress=True,
                reason="Risk estimate exceeds strategic tolerance"
            )

        # 4. Horizon Compatibility Check (Semantic)
        if posture.horizon_days > 7 and intention.metadata.get("origin") == "impulse":
            return StrategicFilterResult(
                allow=False,
                suppress=True,
                reason="Impulse incompatible with long-term horizon"
            )

        # 5. Default: Allow
        return StrategicFilterResult(
            allow=True,
            suppress=False,
            reason="Strategic criteria met"
        )