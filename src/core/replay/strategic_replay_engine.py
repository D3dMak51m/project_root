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
    Strictly scoped to a single StrategicContext.
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
        # 1. Load latest snapshot for THIS context
        bundle = self.backend.load(context)

        if not bundle:
            # Cold start defaults
            return StrategicStateBundle(
                posture=StrategicPosture([], 0.5, 0.5, 1.0, StrategicMode.BALANCED),
                memory=StrategicMemory(),
                trajectory_memory=StrategicTrajectoryMemory(),
                version="1.1"
            )

        # 2. Replay events since snapshot for THIS context
        last_id = bundle.last_event_id
        replay_events = []

        # Fetch history ONLY for this context
        context_history = self.ledger.get_history(context)

        found_snapshot = False
        if last_id is None:
            replay_events = context_history
        else:
            for event in context_history:
                if found_snapshot:
                    replay_events.append(event)
                elif event.id == last_id:
                    found_snapshot = True

            if not found_snapshot and last_id is not None:
                # Log warning or handle gap
                pass

        # 3. Apply Reducers
        current_bundle = bundle
        for event in replay_events:
            try:
                current_bundle = self.reducer.reduce(current_bundle, event)
            except Exception as e:
                raise ReplayIntegrityError(
                    f"Failed to replay event {event.id} ({event.event_type}) for context {context}: {e}")

        return current_bundle