from abc import ABC, abstractmethod
from typing import Dict, Type, Any
from datetime import datetime
from dataclasses import asdict

from src.core.ledger.strategic_event import StrategicEvent
from src.core.persistence.strategic_state_bundle import StrategicStateBundle
from src.core.domain.strategy import StrategicPosture, StrategicMode
from src.core.domain.strategic_memory import StrategicMemory, PathStatus
from src.core.domain.strategic_trajectory import StrategicTrajectoryMemory, StrategicTrajectory, TrajectoryStatus
from src.core.replay.exceptions import ReplayIntegrityError


class StrategicEventReducer(ABC):
    """
    Pure interface for applying an event to a state bundle.
    """

    @abstractmethod
    def reduce(self, bundle: StrategicStateBundle, event: StrategicEvent) -> StrategicStateBundle:
        pass


class StrategyAdaptationReducer(StrategicEventReducer):
    def reduce(self, bundle: StrategicStateBundle, event: StrategicEvent) -> StrategicStateBundle:
        posture_data = event.details.get("posture_after")
        if not posture_data:
            raise ReplayIntegrityError("Missing posture_after in STRATEGY_ADAPTATION event")

        new_posture = StrategicPosture.from_dict(posture_data)

        return StrategicStateBundle(
            posture=new_posture,
            memory=bundle.memory,
            trajectory_memory=bundle.trajectory_memory,
            last_snapshot=bundle.last_snapshot,
            last_event_id=event.id,
            version=bundle.version
        )


class HorizonShiftReducer(StrategicEventReducer):
    def reduce(self, bundle: StrategicStateBundle, event: StrategicEvent) -> StrategicStateBundle:
        posture_data = event.details.get("posture_after")
        if not posture_data:
            raise ReplayIntegrityError("Missing posture_after in HORIZON_SHIFT event")

        new_posture = StrategicPosture.from_dict(posture_data)

        return StrategicStateBundle(
            posture=new_posture,
            memory=bundle.memory,
            trajectory_memory=bundle.trajectory_memory,
            last_snapshot=bundle.last_snapshot,
            last_event_id=event.id,
            version=bundle.version
        )


class TrajectoryUpdateReducer(StrategicEventReducer):
    def reduce(self, bundle: StrategicStateBundle, event: StrategicEvent) -> StrategicStateBundle:
        traj_data = event.details.get("trajectory_after")
        traj_id = event.details.get("trajectory_id")

        if not traj_data or not traj_id:
            raise ReplayIntegrityError("Missing trajectory data in TRAJECTORY_UPDATE event")

        new_trajectory = StrategicTrajectory.from_dict(traj_data)

        new_trajectories = bundle.trajectory_memory.trajectories.copy()
        new_trajectories[traj_id] = new_trajectory

        return StrategicStateBundle(
            posture=bundle.posture,
            memory=bundle.memory,
            trajectory_memory=StrategicTrajectoryMemory(new_trajectories),
            last_snapshot=bundle.last_snapshot,
            last_event_id=event.id,
            version=bundle.version
        )


class PathAbandonmentReducer(StrategicEventReducer):
    def reduce(self, bundle: StrategicStateBundle, event: StrategicEvent) -> StrategicStateBundle:
        path_key_list = event.details.get("path_key")
        status_data = event.details.get("path_status_after")

        if not path_key_list or not status_data:
            raise ReplayIntegrityError("Missing path data in PATH_ABANDONMENT event")

        path_key = tuple(path_key_list)
        new_status = PathStatus.from_dict(status_data)

        new_paths = bundle.memory.paths.copy()
        new_paths[path_key] = new_status

        return StrategicStateBundle(
            posture=bundle.posture,
            memory=StrategicMemory(new_paths),
            trajectory_memory=bundle.trajectory_memory,
            last_snapshot=bundle.last_snapshot,
            last_event_id=event.id,
            version=bundle.version
        )


class RebindingReducer(StrategicEventReducer):
    def reduce(self, bundle: StrategicStateBundle, event: StrategicEvent) -> StrategicStateBundle:
        source_data = event.details.get("source_trajectory_after")
        target_data = event.details.get("target_trajectory_after")

        if not source_data or not target_data:
            raise ReplayIntegrityError("Missing trajectory data in REBINDING event")

        source_traj = StrategicTrajectory.from_dict(source_data)
        target_traj = StrategicTrajectory.from_dict(target_data)

        new_trajectories = bundle.trajectory_memory.trajectories.copy()
        new_trajectories[source_traj.id] = source_traj
        new_trajectories[target_traj.id] = target_traj

        return StrategicStateBundle(
            posture=bundle.posture,
            memory=bundle.memory,
            trajectory_memory=StrategicTrajectoryMemory(new_trajectories),
            last_snapshot=bundle.last_snapshot,
            last_event_id=event.id,
            version=bundle.version
        )


class ReflectionReducer(StrategicEventReducer):
    def reduce(self, bundle: StrategicStateBundle, event: StrategicEvent) -> StrategicStateBundle:
        # Reflection is observational, no state change in bundle except ID
        return StrategicStateBundle(
            posture=bundle.posture,
            memory=bundle.memory,
            trajectory_memory=bundle.trajectory_memory,
            last_snapshot=bundle.last_snapshot,
            last_event_id=event.id,
            version=bundle.version
        )


class CompositeStrategicReducer(StrategicEventReducer):
    """
    Registry and dispatcher for specific reducers.
    """

    def __init__(self):
        self._reducers: Dict[str, StrategicEventReducer] = {
            "STRATEGY_ADAPTATION": StrategyAdaptationReducer(),
            "HORIZON_SHIFT": HorizonShiftReducer(),
            "TRAJECTORY_UPDATE": TrajectoryUpdateReducer(),
            "PATH_ABANDONMENT": PathAbandonmentReducer(),
            "REBINDING": RebindingReducer(),
            "REFLECTION": ReflectionReducer(),
        }

    def reduce(self, bundle: StrategicStateBundle, event: StrategicEvent) -> StrategicStateBundle:
        reducer = self._reducers.get(event.event_type)
        if not reducer:
            raise ReplayIntegrityError(f"Unknown event type: {event.event_type}")

        return reducer.reduce(bundle, event)