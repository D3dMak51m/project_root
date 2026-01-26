from datetime import datetime
from typing import Optional
from src.core.domain.strategic_trajectory import StrategicTrajectory, StrategicTrajectoryMemory, TrajectoryStatus
from src.core.domain.strategic_signals import StrategicSignals
from src.core.domain.strategic_context import StrategicContext
from src.core.domain.execution_intent import ExecutionIntent


class StrategicTrajectoryService:
    """
    Pure service. Updates strategic trajectories based on signals.
    Manages commitment weight and status transitions.
    """

    def update(
            self,
            memory: StrategicTrajectoryMemory,
            signals: StrategicSignals,
            intent: ExecutionIntent,  # [NEW] Intent-aware
            context: StrategicContext,
            now: datetime
    ) -> StrategicTrajectoryMemory:

        # Determine trajectory ID from context (TEMP / PLACEHOLDER for C.18.1)
        # In C.19+, this will use intent metadata or more complex logic.
        trajectory_id = context.domain

        current_trajectory = memory.get_trajectory(trajectory_id)

        if not current_trajectory:
            # Initialize new trajectory if signals are positive
            if signals.outcome_classification == "success":
                new_trajectory = StrategicTrajectory(
                    id=trajectory_id,
                    status=TrajectoryStatus.ACTIVE,
                    commitment_weight=0.1,  # Start low
                    created_at=now,
                    last_updated=now
                )
                new_trajectories = memory.trajectories.copy()
                new_trajectories[trajectory_id] = new_trajectory
                return StrategicTrajectoryMemory(trajectories=new_trajectories)
            return memory

        # Update existing trajectory
        new_weight = current_trajectory.commitment_weight
        new_status = current_trajectory.status

        if signals.outcome_classification == "success":
            # Reinforce commitment
            new_weight = min(1.0, new_weight + 0.05)
            if new_status != TrajectoryStatus.ABANDONED:
                new_status = TrajectoryStatus.ACTIVE

        elif signals.outcome_classification == "hostile_env":
            # Environment resistance -> slight weight drop, potential stall
            new_weight = max(0.0, new_weight - 0.02)
            # If weight drops too low, stall
            if new_weight < 0.2:
                new_status = TrajectoryStatus.STALLED

        elif signals.outcome_classification == "blocked":
            # Policy block -> significant weight drop
            new_weight = max(0.0, new_weight - 0.1)
            if new_weight < 0.1:
                new_status = TrajectoryStatus.ABANDONED

        # Persistence bias from signals can buffer weight loss
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

        return StrategicTrajectoryMemory(trajectories=new_trajectories)