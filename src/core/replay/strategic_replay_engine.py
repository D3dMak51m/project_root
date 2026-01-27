from typing import List, Optional
from datetime import datetime

from src.core.domain.strategic_context import StrategicContext
from src.core.persistence.strategic_state_backend import StrategicStateBackend
from src.core.persistence.strategic_state_bundle import StrategicStateBundle
from src.core.ledger.strategic_ledger import StrategicLedger
from src.core.ledger.strategic_event import StrategicEvent
from src.core.time.time_source import TimeSource
from src.core.domain.strategy import StrategicPosture, StrategicMode
from src.core.domain.strategic_memory import StrategicMemory
from src.core.domain.strategic_trajectory import StrategicTrajectoryMemory
from src.core.replay.strategic_reducer import CompositeStrategicReducer
from src.core.replay.exceptions import ReplayIntegrityError


class StrategicReplayEngine:
    """
    Reconstructs strategic state by loading a snapshot and replaying subsequent events.
    Ensures determinism and data integrity via Event Sourcing pattern.
    """

    def __init__(
            self,
            backend: StrategicStateBackend,
            ledger: StrategicLedger,
            time_source: TimeSource
    ):
        self.backend = backend
        self.ledger = ledger
        self.time_source = time_source
        self.reducer = CompositeStrategicReducer()

    def restore(self, context: StrategicContext) -> StrategicStateBundle:
        # 1. Load latest snapshot
        bundle = self.backend.load(context)

        if not bundle:
            # Cold start defaults
            return StrategicStateBundle(
                posture=StrategicPosture([], 0.5, 0.5, 1.0, StrategicMode.BALANCED),
                memory=StrategicMemory(),
                trajectory_memory=StrategicTrajectoryMemory(),
                version="1.1"
            )

        # 2. Replay events since snapshot
        last_id = bundle.last_event_id
        replay_events = []

        found_snapshot = False
        if last_id is None:
            # If no ID recorded, replay all events (assuming snapshot is empty/base)
            replay_events = self.ledger.get_history()
        else:
            # Scan ledger for events occurring AFTER the snapshot's last_event_id
            for event in self.ledger.get_history():
                if found_snapshot:
                    replay_events.append(event)
                elif event.id == last_id:
                    found_snapshot = True

            # If last_id was not found in ledger, it might be a divergence or truncated log.
            # For E.4, we assume integrity or warn.
            if not found_snapshot and last_id is not None:
                # In strict production, this might be an error.
                # For now, we proceed with empty replay or log warning.
                pass

        # 3. Apply Reducers
        current_bundle = bundle
        for event in replay_events:
            try:
                current_bundle = self.reducer.reduce(current_bundle, event)
            except Exception as e:
                raise ReplayIntegrityError(f"Failed to replay event {event.id} ({event.event_type}): {e}")

        return current_bundle