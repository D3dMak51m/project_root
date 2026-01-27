from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from uuid import uuid4

from src.core.domain.entity import AIHuman
from src.core.domain.strategic_context import StrategicContext
from src.core.domain.execution_intent import ExecutionIntent
from src.core.domain.resource import StrategicResourceBudget, ResourceCost
from src.core.lifecycle.signals import LifeSignals
from src.core.lifecycle.lifeloop import LifeLoop
from src.core.orchestration.strategic_context_runtime import StrategicContextRuntime
from src.core.orchestration.routing_policy import ContextRoutingPolicy, DefaultRoutingPolicy
from src.core.orchestration.arbitrator import StrategicArbitrator, PriorityArbitrator
from src.core.services.resource_manager import StrategicResourceManager
from src.core.time.time_source import TimeSource
from src.core.ledger.strategic_ledger import StrategicLedger
from src.core.persistence.strategic_state_backend import StrategicStateBackend


class StrategicOrchestrator:
    """
    Top-level coordinator for the strategic AI core.
    Manages multiple isolated StrategicContexts, routes signals, and arbitrates execution.
    Owns context lifecycle, tick cadence, arbitration authority, and GLOBAL RESOURCE BUDGET.
    """

    def __init__(
            self,
            time_source: TimeSource,
            ledger: StrategicLedger,
            backend: StrategicStateBackend,
            routing_policy: Optional[ContextRoutingPolicy] = None,
            arbitrator: Optional[StrategicArbitrator] = None,
            resource_manager: Optional[StrategicResourceManager] = None
    ):
        self.time_source = time_source
        self.ledger = ledger
        self.backend = backend
        self.routing_policy = routing_policy or DefaultRoutingPolicy()
        self.arbitrator = arbitrator or PriorityArbitrator()
        self.resource_manager = resource_manager or StrategicResourceManager()

        self._runtimes: Dict[str, StrategicContextRuntime] = {}
        self._last_executed_intent: Optional[ExecutionIntent] = None

        # Initialize Global Budget
        self._budget = StrategicResourceBudget(
            energy_budget=100.0,
            attention_budget=100.0,
            execution_slots=5,
            last_updated=self.time_source.now()
        )

    def register_context(self, context: StrategicContext, human: AIHuman) -> None:
        """
        Registers a new strategic context and initializes its runtime.
        Performs cold-start restore from backend.
        """
        key = str(context)
        if key in self._runtimes:
            return

        # Create isolated LifeLoop for this context
        lifeloop = LifeLoop(
            time_source=self.time_source,
            ledger=self.ledger,
            state_backend=self.backend
            # Observer and policy can be injected if needed
        )

        # Restore state (Bootstrap)
        lifeloop.restore(human, context)

        runtime = StrategicContextRuntime(
            context=context,
            lifeloop=lifeloop,
            tick_count=0,
            active=True
        )
        self._runtimes[key] = runtime

    def remove_context(self, context: StrategicContext) -> None:
        key = str(context)
        if key in self._runtimes:
            del self._runtimes[key]

    def tick(self, human: AIHuman, signals: LifeSignals) -> Optional[ExecutionIntent]:
        """
        Orchestrates a single tick across all relevant contexts.
        1. Recover Resources
        2. Route signals
        3. Tick relevant LifeLoops
        4. Collect intents
        5. Filter Feasible Intents (Budget Check)
        6. Arbitrate
        7. Reserve Budget
        8. Suppress losers
        """
        now = self.time_source.now()

        # 1. Recover Resources
        self._budget = self.resource_manager.recover(self._budget, now)

        # 2. Route Signals
        available_contexts = [r.context for r in self._runtimes.values() if r.active]
        target_contexts = self.routing_policy.resolve(signals, available_contexts)

        candidates: List[Tuple[StrategicContextRuntime, ExecutionIntent]] = []

        # 3. Tick LifeLoops
        for context in target_contexts:
            key = str(context)
            runtime = self._runtimes.get(key)
            if not runtime:
                continue

            runtime.tick_count += 1

            internal_context = runtime.lifeloop.tick(
                human=human,
                signals=signals,
                strategic_context=context,
                tick_count=runtime.tick_count,
                last_executed_intent=self._last_executed_intent
            )

            # 4. Collect Intents
            if internal_context.execution_intent:
                # Intents without cost are invalid and will be filtered out by resource manager
                candidates.append((runtime, internal_context.execution_intent))

        # 5. Filter Feasible Intents (Budget Check)
        feasible_candidates = []
        for runtime, intent in candidates:
            allocation = self.resource_manager.evaluate(intent, self._budget)
            if allocation.approved:
                feasible_candidates.append((runtime, intent))
            else:
                # Suppress immediately if not feasible
                runtime.lifeloop.suppress_pending_intentions(human)

        # 6. Arbitrate
        winner_intent: Optional[ExecutionIntent] = None
        winner_runtime: Optional[StrategicContextRuntime] = None

        if feasible_candidates:
            winner = self.arbitrator.select(feasible_candidates)
            if winner:
                winner_runtime, winner_intent = winner

                # 7. Reserve Budget
                # Strict reservation: Must have cost.
                # If cost is missing (should be caught by evaluate, but double check), fail safe.
                if winner_intent.estimated_cost:
                    self._budget = self.resource_manager.reserve(self._budget, winner_intent.estimated_cost)
                    self._last_executed_intent = winner_intent
                else:
                    # Should be unreachable due to evaluate check, but safe fallback
                    winner_intent = None
                    winner_runtime = None

        # 8. Suppress Losers
        for runtime, intent in feasible_candidates:
            if runtime != winner_runtime:
                runtime.lifeloop.suppress_pending_intentions(human)

        return winner_intent