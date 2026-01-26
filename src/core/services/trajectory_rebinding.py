from datetime import datetime
from typing import List, Tuple

from src.core.domain.strategic_trajectory import StrategicTrajectoryMemory, StrategicTrajectory, TrajectoryStatus
from src.core.domain.strategic_reflection import StrategicReflection, ReflectionOutcome
from src.core.domain.trajectory_rebinding import TrajectoryRebinding
from src.core.domain.strategy import StrategicPosture, StrategicMode


class TrajectoryRebindingService:
    """
    Pure service. Executes trajectory rebinding based on reflections.
    Transfers commitment weight from source to target.
    Enforces mode constraints: TACTICAL mode only allows ABANDON.
    """

    def rebind(
            self,
            memory: StrategicTrajectoryMemory,
            reflections: List[StrategicReflection],
            posture: StrategicPosture,
            now: datetime
    ) -> Tuple[StrategicTrajectoryMemory, List[TrajectoryRebinding]]:

        new_trajectories_map = memory.trajectories.copy()
        rebindings = []

        # TACTICAL Mode Handling: Only process ABANDON
        if posture.mode == StrategicMode.TACTICAL:
            for reflection in reflections:
                if reflection.outcome == ReflectionOutcome.ABANDON:
                    source = memory.get_trajectory(reflection.trajectory_id)
                    if source and source.status != TrajectoryStatus.ABANDONED:
                        new_source = StrategicTrajectory(
                            id=source.id,
                            status=TrajectoryStatus.ABANDONED,
                            commitment_weight=0.0,
                            created_at=source.created_at,
                            last_updated=now
                        )
                        new_trajectories_map[source.id] = new_source

            return StrategicTrajectoryMemory(trajectories=new_trajectories_map), []

        # BALANCED / STRATEGIC Mode Handling

        # Find a suitable target for transformation
        active_candidates = [
            t for t in memory.trajectories.values()
            if t.status == TrajectoryStatus.ACTIVE
        ]
        target_trajectory = None
        if active_candidates:
            target_trajectory = max(active_candidates, key=lambda t: t.commitment_weight)

        for reflection in reflections:
            source = memory.get_trajectory(reflection.trajectory_id)
            if not source:
                continue

            if reflection.outcome == ReflectionOutcome.TRANSFORM and target_trajectory and source.id != target_trajectory.id:
                # Transfer weight
                transfer_amount = source.commitment_weight * 0.8  # Lossy transfer

                # Update Source (Drain)
                new_source = StrategicTrajectory(
                    id=source.id,
                    status=TrajectoryStatus.ABANDONED,
                    commitment_weight=0.0,
                    created_at=source.created_at,
                    last_updated=now
                )
                new_trajectories_map[source.id] = new_source

                # Update Target (Boost)
                current_target = new_trajectories_map.get(target_trajectory.id, target_trajectory)
                new_target_weight = min(1.0, current_target.commitment_weight + transfer_amount)

                new_target = StrategicTrajectory(
                    id=current_target.id,
                    status=current_target.status,
                    commitment_weight=new_target_weight,
                    created_at=current_target.created_at,
                    last_updated=now
                )
                new_trajectories_map[target_trajectory.id] = new_target

                rebindings.append(TrajectoryRebinding(
                    source_trajectory_id=source.id,
                    target_trajectory_id=target_trajectory.id,
                    transferred_weight=transfer_amount,
                    reason=f"Transformed due to {reflection.inferred_cause.name}",
                    created_at=now
                ))

            elif reflection.outcome == ReflectionOutcome.RETRY:
                # Retry: Reset status to ACTIVE, keep weight
                new_source = StrategicTrajectory(
                    id=source.id,
                    status=TrajectoryStatus.ACTIVE,
                    commitment_weight=source.commitment_weight,
                    created_at=source.created_at,
                    last_updated=now
                )
                new_trajectories_map[source.id] = new_source

            elif reflection.outcome == ReflectionOutcome.ABANDON:
                # Finalize abandonment
                if source.status != TrajectoryStatus.ABANDONED or source.commitment_weight > 0:
                    new_source = StrategicTrajectory(
                        id=source.id,
                        status=TrajectoryStatus.ABANDONED,
                        commitment_weight=0.0,
                        created_at=source.created_at,
                        last_updated=now
                    )
                    new_trajectories_map[source.id] = new_source

        return StrategicTrajectoryMemory(trajectories=new_trajectories_map), rebindings