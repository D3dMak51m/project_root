from typing import List, Optional, Set
from datetime import datetime
import json

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
    Acts as the guardian of replay integrity.
    """

    # Canonical set of allowed event types.
    # Any event outside this set is considered corruption/poisoning.
    ALLOWED_EVENT_TYPES: Set[str] = {
        "STRATEGY_ADAPTATION",
        "PATH_ABANDONMENT",
        "TRAJECTORY_UPDATE",
        "REFLECTION",
        "REBINDING",
        "HORIZON_SHIFT"
    }

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
        try:
            bundle = self.backend.load(context)
        except Exception as e:
            raise ReplayIntegrityError(f"Failed to load snapshot for {context}: {e}")

        # If no snapshot, start from default state but DO NOT skip replay
        if not bundle:
            current_bundle = StrategicStateBundle(
                posture=StrategicPosture([], 0.5, 0.5, 1.0, StrategicMode.BALANCED),
                memory=StrategicMemory(),
                trajectory_memory=StrategicTrajectoryMemory(),
                version="1.1"
            )
            last_id = None
        else:
            current_bundle = bundle
            last_id = bundle.last_event_id

        # 2. Replay events since snapshot for THIS context
        replay_events = []

        try:
            context_history = self.ledger.get_history(context)
        except Exception as e:
            raise ReplayIntegrityError(f"Failed to load ledger history for {context}: {e}")

        found_snapshot = False
        if last_id is None:
            # If no ID recorded (or cold start), replay all events
            replay_events = context_history
        else:
            for event in context_history:
                if found_snapshot:
                    replay_events.append(event)
                elif event.id == last_id:
                    found_snapshot = True

            if not found_snapshot and last_id is not None:
                # If history exists but ID not found, it's a gap.
                if context_history:
                    pass

                    # 3. Apply Reducers with Strict Validation
        for event in replay_events:
            # Poisoning Protection: Validate event type against allowlist
            if event.event_type not in self.ALLOWED_EVENT_TYPES:
                raise ReplayIntegrityError(
                    f"Unknown event_type '{event.event_type}' in ledger for {context}. "
                    f"Allowed types: {self.ALLOWED_EVENT_TYPES}"
                )

            # Poisoning Protection: Validate structure
            if not event.details:
                raise ReplayIntegrityError(f"Malformed event {event.id}: missing details")

            try:
                current_bundle = self.reducer.reduce(current_bundle, event)
            except Exception as e:
                raise ReplayIntegrityError(
                    f"Failed to replay event {event.id} ({event.event_type}) for context {context}: {e}")

        return current_bundle