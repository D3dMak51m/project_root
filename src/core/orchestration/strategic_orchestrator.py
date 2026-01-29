from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from uuid import uuid4

from core.domain.budget_snapshot import BudgetSnapshot
from core.domain.execution_result import ExecutionResult, ExecutionStatus
from core.interfaces.execution_adapter import ExecutionAdapter
from core.ledger.budget_event import BudgetEvent
from core.ledger.budget_ledger import BudgetLedger
from core.ledger.in_memory_budget_ledger import InMemoryBudgetLedger
from core.persistence.budget_backend import InMemoryBudgetBackend, BudgetPersistenceBackend
from core.replay.budget_reducer import BudgetReplayReducer
from core.services.strategic_priority import StrategicPriorityService
from infrastructure.adapters.mock_execution_adapter import MockExecutionAdapter
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
            priority_service: Optional[StrategicPriorityService] = None,
            budget_backend: Optional[BudgetPersistenceBackend] = None,
            budget_ledger: Optional[BudgetLedger] = None,
            execution_adapter: Optional[ExecutionAdapter] = None  # [NEW]
    ):
        self.time_source = time_source
        self.ledger = ledger
        self.backend = backend
        self.routing_policy = routing_policy or DefaultRoutingPolicy()
        self.arbitrator = arbitrator or PriorityArbitrator()
        self.resource_manager = resource_manager or StrategicResourceManager()
        self.priority_service = priority_service or StrategicPriorityService()
        self.budget_backend = budget_backend or InMemoryBudgetBackend()
        self.budget_ledger = budget_ledger or InMemoryBudgetLedger()
        self.budget_reducer = BudgetReplayReducer()
        self.execution_adapter = execution_adapter or MockExecutionAdapter()  # [NEW]

        self._runtimes: Dict[str, StrategicContextRuntime] = {}
        self._last_executed_intent: Optional[ExecutionIntent] = None
        self._last_execution_result: Optional[ExecutionResult] = None  # [NEW]

        # Initialize Budget (Event Sourced)
        self._budget = self._restore_budget()

    def _restore_budget(self) -> StrategicResourceBudget:
        snapshot = self.budget_backend.load()
        if snapshot:
            budget = snapshot.budget
            last_id = snapshot.last_event_id
        else:
            budget = StrategicResourceBudget(100.0, 100.0, 5, self.time_source.now())
            last_id = None

        events = self.budget_ledger.get_history()
        replay_events = []
        found_snapshot = False
        if last_id is None:
            replay_events = events
        else:
            for event in events:
                if found_snapshot:
                    replay_events.append(event)
                elif event.id == last_id:
                    found_snapshot = True

        for event in replay_events:
            budget = self.budget_reducer.reduce(budget, event)
        return budget

    def _emit_budget_event(self, event_type: str, delta: Dict[str, float], reason: str, now: datetime) -> None:
        event = BudgetEvent(
            id=uuid4(),
            timestamp=now,
            event_type=event_type,
            delta=delta,
            reason=reason
        )
        self.budget_ledger.record(event)
        self._budget = self.budget_reducer.reduce(self._budget, event)

    def _persist_budget(self, now: datetime):
        history = self.budget_ledger.get_history()
        last_id = history[-1].id if history else None
        snapshot = BudgetSnapshot(
            budget=self._budget,
            timestamp=now,
            last_event_id=last_id,
            version="1.1"
        )
        self.budget_backend.save(snapshot)

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
        2. Inject Feedback (from previous tick) [NEW]
        3. Route signals
        4. Tick relevant LifeLoops
        5. Collect intents
        6. Filter Feasible Intents
        7. Arbitrate
        8. Reserve Budget
        9. Execute (External) [NEW]
        10. Commit/Rollback Budget [NEW]
        11. Suppress losers
        """
        now = self.time_source.now()

        # 1. Recover Resources
        recovery_delta = self.resource_manager.calculate_recovery_delta(self._budget, now)
        if any(v > 0 for v in recovery_delta.values()):
            self._emit_budget_event("BUDGET_RECOVERED", recovery_delta, "Time-based recovery", now)

        # 2. Inject Feedback (from previous tick)
        # If we have a result from the last tick, inject it into signals
        # This ensures the feedback loop is closed in the NEXT tick
        if self._last_execution_result:
            signals.execution_feedback = self._last_execution_result
            self._last_execution_result = None  # Consumed

        # 3. Route Signals
        available_contexts = [r.context for r in self._runtimes.values() if r.active]
        target_contexts = self.routing_policy.resolve(signals, available_contexts)

        candidates: List[Tuple[StrategicContextRuntime, ExecutionIntent]] = []
        runtimes_with_intent = set()

        # 4. Tick LifeLoops
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

            if internal_context.execution_intent:
                intent = internal_context.execution_intent
                if intent.estimated_cost:
                    candidates.append((runtime, intent))
                    runtimes_with_intent.add(key)

        # 5. Filter Feasible
        feasible_candidates = []
        for runtime, intent in candidates:
            allocation = self.resource_manager.evaluate(intent, self._budget)
            if allocation.approved:
                priority = self.priority_service.compute_priority(intent, runtime)
                feasible_candidates.append((runtime, intent, priority))
            else:
                runtime.lifeloop.suppress_pending_intentions(human)

        # 6. Arbitrate
        winner_intent: Optional[ExecutionIntent] = None
        winner_runtime: Optional[StrategicContextRuntime] = None

        if feasible_candidates:
            winner = self.arbitrator.select(feasible_candidates)
            if winner:
                winner_runtime, winner_intent = winner

                # 7. Reserve Budget
                if winner_intent.estimated_cost:
                    reservation_delta = self.resource_manager.calculate_reservation_delta(winner_intent.estimated_cost)
                    self._emit_budget_event("BUDGET_RESERVED", reservation_delta, f"Reservation for {winner_intent.id}",
                                            now)
                    self._last_executed_intent = winner_intent

                    # 8. Execute (External) [NEW]
                    # This is the boundary crossing.
                    execution_result = self.execution_adapter.execute(winner_intent)
                    self._last_execution_result = execution_result

                    # 9. Commit/Rollback Budget [NEW]
                    if execution_result.status in (ExecutionStatus.FAILED, ExecutionStatus.REJECTED):
                        # Rollback reservation
                        # We invert the reservation delta to give it back
                        rollback_delta = {k: -v for k, v in reservation_delta.items()}
                        self._emit_budget_event("BUDGET_ROLLED_BACK", rollback_delta,
                                                f"Rollback for {winner_intent.id}: {execution_result.status.name}", now)
                    # Success implies commit (no-op in E.7/E.9 logic, resources already spent)

                else:
                    winner_intent = None
                    winner_runtime = None

        # 10. Suppress Losers
        for runtime, intent, _ in feasible_candidates:
            if runtime != winner_runtime:
                runtime.lifeloop.suppress_pending_intentions(human)

        # 11. Update Starvation
        for key, runtime in self._runtimes.items():
            if not runtime.active: continue
            is_winner = (runtime == winner_runtime)
            has_intent = (key in runtimes_with_intent)
            runtime.starvation_score = self.priority_service.update_starvation(runtime, is_winner, has_intent)
            if is_winner: runtime.last_win_tick = runtime.tick_count

        # 12. Persist Budget
        self._persist_budget(now)

        return winner_intent