import json
import os
import tempfile
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Optional, Any
from uuid import UUID

from src.core.domain.strategic_context import StrategicContext
from src.core.persistence.strategic_state_backend import StrategicStateBackend
from src.core.persistence.strategic_state_bundle import StrategicStateBundle
from src.core.domain.strategy import StrategicPosture, StrategicMode
from src.core.domain.strategic_memory import StrategicMemory, PathStatus
from src.core.domain.strategic_trajectory import StrategicTrajectoryMemory, StrategicTrajectory, TrajectoryStatus
from src.core.domain.strategic_snapshot import StrategicSnapshot


class FileStrategicStateBackend(StrategicStateBackend):
    """
    File-backed persistence for strategic state.
    Uses JSON serialization with atomic writes.
    """

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def _get_file_path(self, context: StrategicContext) -> str:
        safe_name = str(context).replace("/", "_").replace("*", "ALL")
        return os.path.join(self.base_dir, f"state_{safe_name}.json")

    def _serialize(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, (StrategicMode, TrajectoryStatus)):
            return obj.value
        if is_dataclass(obj):
            return {k: self._serialize(v) for k, v in asdict(obj).items()}
        if isinstance(obj, dict):
            new_dict = {}
            for k, v in obj.items():
                # Safe key serialization: join tuple with pipe
                if isinstance(k, tuple):
                    key_str = "|".join(k)
                else:
                    key_str = str(k)
                new_dict[key_str] = self._serialize(v)
            return new_dict
        if isinstance(obj, list):
            return [self._serialize(i) for i in obj]
        return obj

    def _deserialize_posture(self, data: dict) -> StrategicPosture:
        return StrategicPosture(
            horizon_days=data['horizon_days'],
            engagement_policy=data['engagement_policy'],
            risk_tolerance=data['risk_tolerance'],
            confidence_baseline=data['confidence_baseline'],
            persistence_factor=data['persistence_factor'],
            mode=StrategicMode(data['mode'])
        )

    def _deserialize_memory(self, data: dict) -> StrategicMemory:
        paths = {}
        for k, v in data['paths'].items():
            # Safe key deserialization: split by pipe
            key_tuple = tuple(k.split("|"))

            paths[key_tuple] = PathStatus(
                failure_count=v['failure_count'],
                last_outcome=v['last_outcome'],
                abandonment_level=v['abandonment_level'],
                last_updated=datetime.fromisoformat(v['last_updated']),
                cooldown_until=datetime.fromisoformat(v['cooldown_until']) if v.get('cooldown_until') else None
            )
        return StrategicMemory(paths=paths)

    def _deserialize_trajectory_memory(self, data: dict) -> StrategicTrajectoryMemory:
        trajectories = {}
        for k, v in data['trajectories'].items():
            trajectories[k] = StrategicTrajectory(
                id=v['id'],
                status=TrajectoryStatus(v['status']),
                commitment_weight=v['commitment_weight'],
                created_at=datetime.fromisoformat(v['created_at']),
                last_updated=datetime.fromisoformat(v['last_updated'])
            )
        return StrategicTrajectoryMemory(trajectories=trajectories)

    def load(self, context: StrategicContext) -> Optional[StrategicStateBundle]:
        path = self._get_file_path(context)
        if not os.path.exists(path):
            return None

        try:
            with open(path, 'r') as f:
                data = json.load(f)

            last_event_id = UUID(data['last_event_id']) if data.get('last_event_id') else None

            return StrategicStateBundle(
                posture=self._deserialize_posture(data['posture']),
                memory=self._deserialize_memory(data['memory']),
                trajectory_memory=self._deserialize_trajectory_memory(data['trajectory_memory']),
                last_snapshot=None,
                last_event_id=last_event_id,
                version=data.get('version', "1.1")
            )
        except Exception as e:
            print(f"Error loading state for {context}: {e}")
            return None

    def save(self, context: StrategicContext, bundle: StrategicStateBundle) -> None:
        path = self._get_file_path(context)
        data = self._serialize(bundle)

        dir_name = os.path.dirname(path)
        with tempfile.NamedTemporaryFile('w', dir=dir_name, delete=False) as tmp_file:
            json.dump(data, tmp_file, indent=2)
            tmp_name = tmp_file.name

        os.replace(tmp_name, path)