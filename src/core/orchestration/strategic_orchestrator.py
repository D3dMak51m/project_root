from typing import Dict, List, Optional, Tuple
from datetime import datetime

from src.core.domain.entity import AIHuman
from src.core.domain.strategic_context import StrategicContext
from src.core.domain.execution_intent import ExecutionIntent
from src.core.lifecycle.signals import LifeSignals
from src.core.lifecycle.lifeloop import LifeLoop
from src.core.orchestration.strategic_context_runtime import StrategicContextRuntime
from src.core.orchestration.routing_policy import ContextRoutingPolicy, DefaultRoutingPolicy
from src.core.orchestration.arbitrator import StrategicArbitrator, PriorityArbitrator
from src.core.time.time_source import TimeSource
from src.core.ledger.strategic_ledger import StrategicLedger
from src.core.persistence.strategic_state_backend import StrategicStateBackend


class StrategicOrchestrator:
    """
    Top-level coordinator for the strategic AI core.
    Manages multiple isolated StrategicContexts, routes signals, and arbitrates execution.
    Owns context lifecycle, tick cadence, and arbitration authority.
    """

    def __init__(
            self,
            time_source: TimeSource,
            ledger: StrategicLedger,
            backend: StrategicStateBackend,
            routing_policy: Optional[ContextRoutingPolicy] = None,
            arbitrator: Optional[StrategicArbitrator] = None
    ):
        self.time_source = time_source
        self.ledger = ledger
        self.backend = backend
        self.routing_policy = routing_policy or DefaultRoutingPolicy()
        self.arbitrator = arbitrator or PriorityArbitrator()

        self._runtimes: Dict[str, StrategicContextRuntime] = {}
        self._last_executed_intent: Optional[ExecutionIntent] = None  # [NEW]

    # ... register_context, remove_context ... (unchanged)

    def tick(self, human: AIHuman, signals: LifeSignals) -> Optional[ExecutionIntent]:
        """
        Orchestrates a single tick across all relevant contexts.
        1. Route signals
        2. Tick relevant LifeLoops (passing tick_count and last_intent)
        3. Collect intents
        4. Arbitrate
        5. Suppress losers
        """
        now = self.time_source.now()

        # 1. Route Signals
        available_contexts = [r.context for r in self._runtimes.values() if r.active]
        target_contexts = self.routing_policy.resolve(signals, available_contexts)

        candidates: List[Tuple[StrategicContextRuntime, ExecutionIntent]] = []

        # 2. Tick LifeLoops
        for context in target_contexts:
            key = str(context)
            runtime = self._runtimes.get(key)
            if not runtime:
                continue

            # Increment tick count at orchestrator level
            runtime.tick_count += 1

            # Execute tick within specific context
            internal_context = runtime.lifeloop.tick(
                human=human,
                signals=signals,
                strategic_context=context,
                tick_count=runtime.tick_count,  # [NEW] Pass explicit tick count
                last_executed_intent=self._last_executed_intent  # [NEW] Pass causality
            )

            # 3. Collect Intents
            if internal_context.execution_intent:
                candidates.append((runtime, internal_context.execution_intent))

        # 4. Arbitrate
        winner_intent: Optional[ExecutionIntent] = None
        winner_runtime: Optional[StrategicContextRuntime] = None

        if candidates:
            winner = self.arbitrator.select(candidates)
            if winner:
                winner_runtime, winner_intent = winner
                self._last_executed_intent = winner_intent  # [NEW] Update causality

        # 5. Suppress Losers [NEW]
        for runtime, intent in candidates:
            if runtime != winner_runtime:
                # Suppress pending intentions in losing contexts
                runtime.lifeloop.suppress_pending_intentions(human)

        return winner_intent