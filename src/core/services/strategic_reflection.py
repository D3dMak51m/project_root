from datetime import datetime
from typing import List, Optional

from src.core.domain.strategic_trajectory import StrategicTrajectoryMemory, TrajectoryStatus
from src.core.domain.strategic_memory import StrategicMemory
from src.core.domain.strategy import StrategicPosture, StrategicMode
from src.core.domain.strategic_context import StrategicContext
from src.core.domain.strategic_reflection import StrategicReflection, ReflectionOutcome, InferredCause


class StrategicReflectionService:
    """
    Pure service. Analyzes stalled or abandoned trajectories to determine future course.
    """

    def reflect(
            self,
            trajectory_memory: StrategicTrajectoryMemory,
            strategic_memory: StrategicMemory,
            posture: StrategicPosture,
            context: StrategicContext,
            now: datetime
    ) -> List[StrategicReflection]:

        reflections = []

        # Analyze STALLED and ABANDONED trajectories
        candidates = [
            t for t in trajectory_memory.trajectories.values()
            if t.status in (TrajectoryStatus.STALLED, TrajectoryStatus.ABANDONED)
        ]

        for t in candidates:
            # Skip if recently updated (give it time to settle)
            if (now - t.last_updated).total_seconds() < 60:
                continue

            # Determine Cause
            # Check path status in strategic memory
            # Simplified path key construction for C.20 (using trajectory ID as domain)
            path_key = (t.id,)
            path_status = strategic_memory.get_status(path_key)

            cause = InferredCause.UNKNOWN
            if path_status.abandonment_level == "hard":
                cause = InferredCause.POLICY
            elif path_status.abandonment_level == "soft":
                cause = InferredCause.ENVIRONMENT
            elif t.commitment_weight < 0.1:
                cause = InferredCause.RESOURCE

            # Determine Outcome
            outcome = ReflectionOutcome.ABANDON
            confidence_adj = 0.0

            if posture.mode == StrategicMode.TACTICAL:
                # Tactical mode -> ruthless abandonment
                outcome = ReflectionOutcome.ABANDON
                confidence_adj = -0.05
            else:
                if cause == InferredCause.POLICY:
                    outcome = ReflectionOutcome.ABANDON
                    confidence_adj = -0.1
                elif cause == InferredCause.ENVIRONMENT:
                    # If environment is hostile but we are strategic, maybe transform?
                    if posture.mode == StrategicMode.STRATEGIC:
                        outcome = ReflectionOutcome.TRANSFORM
                        confidence_adj = 0.05
                    else:
                        outcome = ReflectionOutcome.ABANDON
                elif cause == InferredCause.RESOURCE:
                    # Starved for resources -> Transform/Merge into stronger line
                    outcome = ReflectionOutcome.TRANSFORM
                    confidence_adj = 0.0
                elif cause == InferredCause.UNKNOWN:
                    # If unknown and not hard blocked, maybe retry?
                    if t.status == TrajectoryStatus.STALLED:
                        outcome = ReflectionOutcome.RETRY
                    else:
                        outcome = ReflectionOutcome.ABANDON

            reflections.append(StrategicReflection(
                trajectory_id=t.id,
                outcome=outcome,
                inferred_cause=cause,
                confidence_adjustment=confidence_adj,
                generated_at=now
            ))

        return reflections