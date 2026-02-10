from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass

from src.core.domain.strategic_trajectory import StrategicTrajectoryMemory, TrajectoryStatus, StrategicTrajectory
from src.core.domain.strategy import StrategicPosture, StrategicMode
from src.core.domain.strategic_signals import StrategicSignals


@dataclass(frozen=True)
class CompetitionDiagnostics:
    displaced: List[str]
    budget_capped: List[str]
    decayed: List[str]
    reason: str


class TrajectoryCompetitionService:
    """
    Pure service. Manages competition between strategic trajectories.
    Enforces resource limits (commitment budget) and mode constraints.
    Applies semantic boosting and temporal decay.
    """

    def compete(
            self,
            memory: StrategicTrajectoryMemory,
            posture: StrategicPosture,
            signals: Optional[StrategicSignals],
            now: datetime
    ) -> Tuple[StrategicTrajectoryMemory, CompetitionDiagnostics]:

        displaced = []
        budget_capped = []
        decayed = []

        # 1. Filter Active/Stalled Trajectories
        active_trajectories = [
            t for t in memory.trajectories.values()
            if t.status in (TrajectoryStatus.ACTIVE, TrajectoryStatus.STALLED)
        ]

        if not active_trajectories:
            return memory, CompetitionDiagnostics([], [], [], "No active trajectories")

        # 2. Apply Semantic Boost & Decay (Pre-Sort)
        processed_trajectories = []

        for t in active_trajectories:
            temp_weight = t.commitment_weight
            temp_status = t.status

            # A. Semantic Boost (Transient)
            # If this trajectory was just successful, boost its priority for sorting
            # We don't persist this boost directly, but use it for sorting order.
            # However, we need to know WHICH trajectory was successful.
            # Since we don't have trajectory_id in signals, we rely on last_updated.
            # If updated very recently (this tick) and signal is success -> boost.
            is_recent = (now - t.last_updated).total_seconds() < 1.0
            priority_boost = 0.0

            if is_recent and signals:
                if signals.outcome_classification == "success":
                    priority_boost = 0.2
                elif signals.outcome_classification == "blocked":
                    priority_boost = -0.2

            # B. Stalled Decay
            if t.status == TrajectoryStatus.STALLED:
                days_since_update = (now - t.last_updated).days
                if days_since_update > 7:
                    decay_amount = 0.05 * (days_since_update - 7)
                    temp_weight = max(0.0, temp_weight - decay_amount)
                    if temp_weight < 0.1:
                        temp_status = TrajectoryStatus.ABANDONED
                        decayed.append(t.id)

            processed_trajectories.append({
                "trajectory": t,
                "sort_weight": temp_weight + priority_boost,
                "final_weight": temp_weight,
                "final_status": temp_status
            })

        # 3. Sort by Priority
        # Priority: Status (ACTIVE > STALLED) -> Boosted Weight -> Recency
        def priority_key(item):
            t = item["trajectory"]
            status_score = 1.0 if item["final_status"] == TrajectoryStatus.ACTIVE else 0.0
            return (status_score, item["sort_weight"], t.last_updated)

        sorted_items = sorted(processed_trajectories, key=priority_key, reverse=True)

        # 4. Enforce Mode Constraints (Max Active Count)
        max_active = float('inf')
        if posture.mode == StrategicMode.TACTICAL:
            max_active = 1
        elif posture.mode == StrategicMode.BALANCED:
            max_active = 2

        # 5. Allocate Budget (Total 1.0)
        budget = 1.0
        new_trajectories_map = memory.trajectories.copy()

        active_count = 0

        for item in sorted_items:
            t = item["trajectory"]
            new_status = item["final_status"]
            new_weight = item["final_weight"]

            # Skip already abandoned
            if new_status == TrajectoryStatus.ABANDONED:
                updated_t = StrategicTrajectory(
                    id=t.id, status=new_status, commitment_weight=new_weight,
                    created_at=t.created_at, last_updated=now
                )
                new_trajectories_map[t.id] = updated_t
                continue

            # Check mode limit
            if active_count >= max_active:
                if new_status == TrajectoryStatus.ACTIVE:
                    new_status = TrajectoryStatus.STALLED
                    displaced.append(t.id)

            if new_status == TrajectoryStatus.ACTIVE:
                active_count += 1

            # Check budget
            if budget <= 0:
                new_status = TrajectoryStatus.ABANDONED
                new_weight = 0.0
                budget_capped.append(t.id)
            elif new_weight > budget:
                new_weight = budget
                budget = 0.0
                budget_capped.append(t.id)
            else:
                budget -= new_weight

            # Update if changed
            if new_status != t.status or new_weight != t.commitment_weight:
                updated_t = StrategicTrajectory(
                    id=t.id,
                    status=new_status,
                    commitment_weight=new_weight,
                    created_at=t.created_at,
                    last_updated=now
                )
                new_trajectories_map[t.id] = updated_t

        return StrategicTrajectoryMemory(trajectories=new_trajectories_map), CompetitionDiagnostics(
            displaced=displaced,
            budget_capped=budget_capped,
            decayed=decayed,
            reason="Competition cycle complete"
        )