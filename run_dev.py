import sys
import os
from datetime import datetime, timezone
from uuid import uuid4

# Ensure src is in python path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.core.time.system_time_source import SystemTimeSource
from src.core.ledger.in_memory_ledger import InMemoryStrategicLedger
from src.core.persistence.in_memory_backend import InMemoryStrategicStateBackend
from src.core.orchestration.strategic_orchestrator import StrategicOrchestrator
from src.core.lifecycle.signals import LifeSignals
from src.core.observability.null_observer import NullStrategicObserver
from src.core.domain.entity import AIHuman
from src.core.domain.identity import Identity
from src.core.domain.behavior import BehaviorState
from src.core.domain.memory import MemorySystem
from src.core.domain.stance import Stance
from src.core.domain.readiness import ActionReadiness
from src.core.domain.strategy import StrategicPosture, StrategicMode
from src.core.domain.strategic_context import StrategicContext
from src.core.domain.persona import PersonaMask


def main():
    print("Initializing DEV environment...")

    # 1. Infrastructure
    time_source = SystemTimeSource()
    ledger = InMemoryStrategicLedger()
    backend = InMemoryStrategicStateBackend()
    observer = NullStrategicObserver()

    # 2. Orchestrator
    orchestrator = StrategicOrchestrator(
        time_source=time_source,
        ledger=ledger,
        backend=backend,
        observer=observer
    )

    # 3. AIHuman
    # Using direct instantiation as no factory method exists in the provided context for AIHuman creation from scratch.
    # The prompt says "Find and use EXISTING factory... If restore is used - load empty state".
    # Orchestrator.register_context calls LifeLoop.restore which loads from backend.
    # But we need an AIHuman instance to pass to register_context.
    # We will create a minimal valid AIHuman.

    human = AIHuman(
        id=uuid4(),
        identity=Identity("DevSubject", 0, "N/A", "Dev Bio", [], [], {}),
        state=BehaviorState(100.0, 100.0, 0.0, time_source.now(), False),
        memory=MemorySystem([], []),
        stance=Stance({}),
        readiness=ActionReadiness(50.0, 40.0, 80.0),
        intentions=[],
        personas=[
            PersonaMask(
                id=uuid4(),
                human_id=uuid4(),
                platform="dev",
                display_name="DevBot",
                bio="",
                language="en",
                tone="neutral",
                verbosity="medium",
                activity_rate=1.0,
                risk_tolerance=1.0,
                posting_hours=list(range(24))
            )
        ],
        strategy=StrategicPosture([], 0.5, 0.5, 1.0, StrategicMode.BALANCED),
        deferred_actions=[],
        created_at=time_source.now()
    )

    # 4. Register Context
    context = StrategicContext("global", None, None, "dev_domain")
    orchestrator.register_context(context, human)

    # 5. Run Loop
    print("Starting LifeLoop (10 ticks)...")

    for i in range(1, 11):
        signals = LifeSignals(
            pressure_delta=0.0,
            energy_delta=0.0,
            attention_delta=0.0,
            rest=False,
            perceived_topics={},
            memories=[],
            execution_feedback=None
        )

        intent = orchestrator.tick(human, signals)

        status = "SILENT"
        if intent:
            status = f"INTENT: {intent.abstract_action} (ID: {intent.id})"

        print(f"Tick {i}: {status}")

    print("Dev run complete.")


if __name__ == "__main__":
    main()