from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from uuid import uuid4

from core.services.strategic_priority import StrategicPriorityService
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
            resource_manager: Optional[StrategicResourceManager] = None,
            priority_service: Optional[StrategicPriorityService] = None
    ):
        self.time_source = time_source
        self.ledger = ledger
        self.backend = backend
        self.routing_policy = routing_policy or DefaultRoutingPolicy()
        self.arbitrator = arbitrator or PriorityArbitrator()
        self.resource_manager = resource_manager or StrategicResourceManager()
        self.priority_service = priority_service or StrategicPriorityService()

        self._runtimes: Dict[str, StrategicContextRuntime] = {}
        self._last_executed_intent: Optional[ExecutionIntent] = None

        self._budget = StrategicResourceBudget(
            energy_budget=100.0,
            attention_budget=100.0,
            execution_slots=5,
            last_updated=self.time_source.now()
        )

    def register_context(self, context: StrategicContext, human: AIHuman) -> None:
        key = str(context)
        if key in self._runtimes:
            return

        lifeloop = LifeLoop(
            time_source=self.time_source,
            ledger=self.ledger,
            state_backend=self.backend
        )

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
        6. Compute Priorities [NEW]
        7. Arbitrate
        8. Reserve Budget
        9. Update Starvation [NEW]
        10. Suppress losers
        """
        now = self.time_source.now()

        # 1. Recover Resources
        self._budget = self.resource_manager.recover(self._budget, now)

        # 2. Route Signals
        available_contexts = [r.context for r in self._runtimes.values() if r.active]
        target_contexts = self.routing_policy.resolve(signals, available_contexts)

        # List of (Runtime, Intent)
        raw_candidates: List[Tuple[StrategicContextRuntime, ExecutionIntent]] = []
        # Track which runtimes produced an intent for starvation logic
        runtimes_with_intent = set()

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
                intent = internal_context.execution_intent
                # Ensure cost exists (E.7 fix assumption: binding sets it)
                if not intent.estimated_cost:
                    # Fallback or skip? E.7 said strict reject.
                    # We skip if no cost.
                    pass
                else:
                    raw_candidates.append((runtime, intent))
                    runtimes_with_intent.add(key)

        # 5. Filter Feasible Intents & 6. Compute Priorities
        # List of (Runtime, Intent, PriorityScore)
        arbitration_candidates: List[Tuple[StrategicContextRuntime, ExecutionIntent, float]] = []

        for runtime, intent in raw_candidates:
            allocation = self.resource_manager.evaluate(intent, self._budget)
            if allocation.approved:
                priority = self.priority_service.compute_priority(intent, runtime)
                arbitration_candidates.append((runtime, intent, priority))
            else:
                # Suppress immediately if not feasible
                runtime.lifeloop.suppress_pending_intentions(human)

        # 7. Arbitrate
        winner_intent: Optional[ExecutionIntent] = None
        winner_runtime: Optional[StrategicContextRuntime] = None

        if arbitration_candidates:
            winner = self.arbitrator.select(arbitration_candidates)
            if winner:
                winner_runtime, winner_intent = winner

                # 8. Reserve Budget
                if winner_intent.estimated_cost:
                    self._budget = self.resource_manager.reserve(self._budget, winner_intent.estimated_cost)
                    self._last_executed_intent = winner_intent
                else:
                    # Should be unreachable
                    winner_intent = None
                    winner_runtime = None

        # 9. Update Starvation & 10. Suppress Losers
        # Iterate over ALL active runtimes to update starvation
        for key, runtime in self._runtimes.items():
            if not runtime.active:
                continue

            is_winner = (runtime == winner_runtime)
            has_intent = (key in runtimes_with_intent)

            # Update starvation score
            runtime.starvation_score = self.priority_service.update_starvation(
                runtime, is_winner, has_intent
            )

            if is_winner:
                runtime.last_win_tick = runtime.tick_count

            # Suppress if had intent but didn't win (either infeasible or lost arbitration)
            if has_intent and not is_winner:
                runtime.lifeloop.suppress_pending_intentions(human)

        return winner_intent