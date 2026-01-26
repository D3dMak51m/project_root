from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple
from src.core.domain.intention import Intention
from src.core.domain.strategy import StrategicPosture, StrategicMode
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
    Memory-aware: checks for path abandonment.
    Mode-aware: checks for horizon/risk compatibility.
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
            if path_status.cooldown_until and now < path_status.cooldown_until:
                return StrategicFilterResult(
                    allow=False,
                    suppress=True,
                    reason=f"Path {path_key} is soft-abandoned (cooldown active)"
                )

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

        # 4. Horizon/Mode Compatibility Check (Semantic) [NEW]
        # TACTICAL mode suppresses long-horizon or high-risk intents
        if posture.mode == StrategicMode.TACTICAL:
            if intention.metadata.get("horizon", "short") == "long":
                return StrategicFilterResult(
                    allow=False,
                    suppress=True,
                    reason="Long-horizon intention suppressed in TACTICAL mode"
                )
            # Stricter risk check in tactical mode
            if intention_risk > 0.3:
                return StrategicFilterResult(
                    allow=False,
                    suppress=True,
                    reason="Moderate risk suppressed in TACTICAL mode"
                )

        # STRATEGIC mode allows investment-like intents (no specific suppression here, just permissive)

        # 5. Default: Allow
        return StrategicFilterResult(
            allow=True,
            suppress=False,
            reason="Strategic criteria met"
        )