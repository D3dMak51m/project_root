from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from src.core.domain.intention import Intention
from src.core.domain.strategy import StrategicPosture
from src.core.domain.readiness import ActionReadiness


@dataclass(frozen=True)
class StrategicFilterResult:
    allow: bool
    defer: bool
    suppress: bool
    reason: str
    suggested_resume_after: Optional[datetime] = None


class StrategicFilterService:
    """
    Pure service. Evaluates intentions against the current strategic posture.
    Acts as a cold veto layer: suppresses, defers, or allows intentions.
    """

    def evaluate(
            self,
            intention: Intention,
            posture: StrategicPosture,
            readiness: ActionReadiness,
            now: datetime
    ) -> StrategicFilterResult:

        # 1. Intervention Threshold Check
        if readiness.value < posture.intervention_threshold:
            return StrategicFilterResult(
                allow=False,
                defer=False,
                suppress=True,
                reason="Readiness below intervention threshold"
            )

        # 2. Engagement Policy Check
        if any(policy in intention.type for policy in posture.engagement_policy):
            return StrategicFilterResult(
                allow=False,
                defer=False,
                suppress=True,
                reason="Forbidden by engagement policy"
            )

        # 3. Patience Level Check (Deferral)
        if float(intention.priority) < posture.patience_level:
            # Defer for a period proportional to the gap
            defer_hours = (posture.patience_level - intention.priority) * 2.0
            resume_at = now + timedelta(hours=defer_hours)

            return StrategicFilterResult(
                allow=False,
                defer=True,
                suppress=False,
                reason="Priority below patience level",
                suggested_resume_after=resume_at
            )

        # 4. Default: Allow
        return StrategicFilterResult(
            allow=True,
            defer=False,
            suppress=False,
            reason="Strategic criteria met"
        )