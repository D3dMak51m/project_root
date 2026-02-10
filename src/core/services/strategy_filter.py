from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple
from src.core.domain.intention import Intention
from src.core.domain.strategy import StrategicPosture, StrategicMode
from src.core.domain.strategic_memory import StrategicMemory
from src.core.domain.strategic_trajectory import StrategicTrajectoryMemory, TrajectoryStatus
from src.core.domain.strategic_context import StrategicContext
from src.core.services.path_key import extract_path_key


@dataclass(frozen=True)
class StrategicFilterResult:
    allow: bool
    suppress: bool
    reason: str


class StrategicFilterService:
    """
    Pure service. Evaluates intentions against strategic posture, memory, and trajectories.
    Acts as a cold SEMANTIC veto layer.
    """

    def evaluate(
            self,
            intention: Intention,
            posture: StrategicPosture,
            memory: StrategicMemory,
            trajectory_memory: StrategicTrajectoryMemory,
            context: StrategicContext,
            now: datetime
    ) -> StrategicFilterResult:

        path_key = extract_path_key(intention, context)
        path_status = memory.get_status(path_key)

        # Get relevant trajectory
        trajectory_id = context.domain
        trajectory = trajectory_memory.get_trajectory(trajectory_id)

        # Trajectory Influence Calculation
        trajectory_bonus = 0.0
        if trajectory and trajectory.status == TrajectoryStatus.ACTIVE:
            trajectory_bonus = trajectory.commitment_weight * 0.2

        # [NEW] Trajectory Status Check
        # In TACTICAL mode, suppress intentions not belonging to ACTIVE trajectories
        # unless it's a new exploration (no trajectory yet)
        if posture.mode == StrategicMode.TACTICAL:
            if trajectory and trajectory.status != TrajectoryStatus.ACTIVE:
                return StrategicFilterResult(
                    allow=False,
                    suppress=True,
                    reason="Non-active trajectory suppressed in TACTICAL mode"
                )

        # 1. Strategic Memory Check (Abandonment) - HARD GATE
        if path_status.abandonment_level == "hard":
            return StrategicFilterResult(
                allow=False,
                suppress=True,
                reason=f"Path {path_key} is hard-abandoned"
            )

        if path_status.abandonment_level == "soft":
            can_override_soft = (
                    posture.mode != StrategicMode.TACTICAL and
                    trajectory and
                    trajectory.commitment_weight > 0.7
            )

            if not can_override_soft:
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
        effective_tolerance = posture.risk_tolerance + trajectory_bonus

        if intention_risk > effective_tolerance:
            return StrategicFilterResult(
                allow=False,
                suppress=True,
                reason="Risk estimate exceeds strategic tolerance"
            )

        # 4. Horizon/Mode Compatibility Check (Semantic)
        if posture.mode == StrategicMode.TACTICAL:
            if intention.metadata.get("horizon", "short") == "long":
                return StrategicFilterResult(
                    allow=False,
                    suppress=True,
                    reason="Long-horizon intention suppressed in TACTICAL mode"
                )
            if intention_risk > 0.3:
                return StrategicFilterResult(
                    allow=False,
                    suppress=True,
                    reason="Moderate risk suppressed in TACTICAL mode"
                )

        # 5. Default: Allow
        return StrategicFilterResult(
            allow=True,
            suppress=False,
            reason="Strategic criteria met"
        )