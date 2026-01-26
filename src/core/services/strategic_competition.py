from datetime import datetime
from typing import Optional
from src.core.domain.strategic_trajectory import StrategicTrajectory, StrategicTrajectoryMemory, TrajectoryStatus
from src.core.domain.strategic_signals import StrategicSignals
from src.core.domain.strategic_context import StrategicContext
from src.core.domain.execution_intent import ExecutionIntent
from src.core.domain.strategy import StrategicPosture
from src.core.services.trajectory_competition import TrajectoryCompetitionService


class StrategicTrajectoryService:
    """
    Pure service. Updates strategic trajectories based on signals.
    Manages commitment weight and status transitions.
    Integrates competition logic.
    """

    def __init__(self):
        self.competition_service = TrajectoryCompetitionService()

    def update(
            self,
            memory: StrategicTrajectoryMemory,
            signals: StrategicSignals,
            intent: ExecutionIntent,
            context: StrategicContext,
            posture: StrategicPosture,  # [NEW] Needed for competition
            now: datetime
    ) -> StrategicTrajectoryMemory:

        # 1. Local Update (Existing Logic)
        # Determine trajectory ID from context (TEMP / PLACEHOLDER for C.18.1)
        trajectory_id = context.domain

        current_trajectory = memory.get_trajectory(trajectory_id)
        updated_memory = memory

        if not current_trajectory:
            if signals.outcome_classification == "success":
                new_trajectory = StrategicTrajectory(
                    id=trajectory_id,
                    status=TrajectoryStatus.ACTIVE,
                    commitment_weight=0.1,
                    created_at=now,
                    last_updated=now
                )
                new_trajectories = memory.trajectories.copy()
                new_trajectories[trajectory_id] = new_trajectory
                updated_memory = StrategicTrajectoryMemory(trajectories=new_trajectories)
        else:
            new_weight = current_trajectory.commitment_weight
            new_status = current_trajectory.status

            if signals.outcome_classification == "success":
                new_weight = min(1.0, new_weight + 0.05)
                if new_status != TrajectoryStatus.ABANDONED:
                    new_status = TrajectoryStatus.ACTIVE
            elif signals.outcome_classification == "hostile_env":
                new_weight = max(0.0, new_weight - 0.02)
                if new_weight < 0.2:
                    new_status = TrajectoryStatus.STALLED
            elif signals.outcome_classification == "blocked":
                new_weight = max(0.0, new_weight - 0.1)
                if new_weight < 0.1:
                    new_status = TrajectoryStatus.ABANDONED

            if signals.persistence_bias > 1.0:
                new_weight = min(1.0, new_weight + 0.01)

            updated_trajectory = StrategicTrajectory(
                id=current_trajectory.id,
                status=new_status,
                commitment_weight=new_weight,
                created_at=current_trajectory.created_at,
                last_updated=now
            )

            new_trajectories = memory.trajectories.copy()
            new_trajectories[trajectory_id] = updated_trajectory
            updated_memory = StrategicTrajectoryMemory(trajectories=new_trajectories)

        # 2. Global Competition (New Logic)
        final_memory = self.competition_service.compete(
            updated_memory,
            posture,
            now
        )

        return final_memory