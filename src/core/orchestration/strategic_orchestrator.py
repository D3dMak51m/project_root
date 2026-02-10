from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from uuid import uuid4

from governance.runtime.governance_runtime_context import RuntimeGovernanceContext
from src.core.domain.entity import AIHuman
from src.core.domain.strategic_context import StrategicContext
from src.core.domain.execution_intent import ExecutionIntent
from src.core.domain.resource import StrategicResourceBudget, ResourceCost
from src.core.domain.budget_snapshot import BudgetSnapshot
from src.core.domain.execution_result import ExecutionResult, ExecutionStatus
from src.core.lifecycle.signals import LifeSignals
from src.core.lifecycle.lifeloop import LifeLoop
from src.core.orchestration.strategic_context_runtime import StrategicContextRuntime
from src.core.orchestration.routing_policy import ContextRoutingPolicy, DefaultRoutingPolicy
from src.core.orchestration.arbitrator import StrategicArbitrator, PriorityArbitrator
from src.core.services.resource_manager import StrategicResourceManager
from src.core.services.strategic_priority import StrategicPriorityService
from src.core.time.time_source import TimeSource
from src.core.ledger.strategic_ledger import StrategicLedger
from src.core.ledger.budget_ledger import BudgetLedger
from src.core.ledger.in_memory_budget_ledger import InMemoryBudgetLedger
from src.core.ledger.budget_event import BudgetEvent
from src.core.persistence.strategic_state_backend import StrategicStateBackend
from src.core.persistence.budget_backend import BudgetPersistenceBackend, InMemoryBudgetBackend
from src.core.replay.budget_reducer import BudgetReplayReducer
from src.core.interfaces.execution_adapter import ExecutionAdapter
from src.infrastructure.adapters.mock_execution_adapter import MockExecutionAdapter
from src.core.replay.strategic_replay_engine import StrategicReplayEngine
from src.core.observability.strategic_observer import StrategicObserver
from src.core.observability.null_observer import NullStrategicObserver
from src.core.observability.telemetry_event import TelemetryEvent
from src.core.domain.runtime_phase import RuntimePhase
from src.integration.registry import ExecutionAdapterRegistry
from src.integration.normalizer import ResultNormalizer
from src.core.config.runtime_profile import RuntimeProfile, Environment
from src.core.domain.exceptions import SafetyLimitExceeded, PanicMode
from src.governance.runtime.governance_runtime_provider import GovernanceRuntimeProvider
from src.admin.interfaces.governance_service import GovernanceService
from src.autonomy.services.governance_execution_resolver import StandardGovernanceExecutionResolver
from src.autonomy.domain.execution_gate_decision import ExecutionGateDecision
from src.autonomy.services.governance_autonomy_resolver import StandardGovernanceAutonomyResolver
from src.interaction.services.governance_policy_resolver import StandardGovernancePolicyResolver
from src.memory.store.memory_store import MemoryStore
from src.memory.services.memory_ingestion import MemoryIngestionService
from src.memory.services.memory_query import MemoryQueryService
from src.memory.domain.event_record import EventRecord
from src.memory.domain.governance_snapshot import GovernanceSnapshot
from src.autonomy.domain.autonomy_state import AutonomyState
from src.autonomy.domain.autonomy_mode import AutonomyMode
from src.interaction.domain.policy_decision import PolicyDecision
from src.memory.interfaces.memory_id_source import MemoryIdSource, SystemMemoryIdSource
from src.memory.services.memory_decay_policy import LinearDecay
from src.memory.services.temporal_memory_analyzer import TemporalMemoryAnalyzer
from src.memory.services.memory_signal_builder import MemorySignalBuilder
from src.memory.services.memory_strategy_adapter import MemoryStrategyAdapter
from src.memory.services.memory_scope_resolver import MemoryScopeResolver
from src.memory.store.counterfactual_memory_store import CounterfactualMemoryStore
from src.memory.services.counterfactual_analyzer import CounterfactualAnalyzer
from src.memory.domain.counterfactual_event import CounterfactualEvent
from src.memory.services.learning_extractor import LearningExtractor
from src.memory.services.learning_policy_adapter import LearningPolicyAdapter
from src.memory.domain.strategic_learning_signal import StrategicLearningSignal
from src.memory.domain.meta_learning_policy import MetaLearningPolicy
from src.memory.domain.meta_learning_context import MetaLearningContext
from src.memory.services.meta_learning_resolver import MetaLearningResolver


class StrategicOrchestrator:
    """
    Top-level coordinator for the strategic AI core.
    Manages multiple isolated StrategicContexts, routes signals, and arbitrates execution.
    Owns context lifecycle, tick cadence, arbitration authority, and GLOBAL RESOURCE BUDGET.
    Enforces RuntimeProfile safety limits.
    """

    def __init__(
            self,
            time_source: TimeSource,
            ledger: StrategicLedger,
            backend: StrategicStateBackend,
            profile: Optional[RuntimeProfile] = None,
            routing_policy: Optional[ContextRoutingPolicy] = None,
            arbitrator: Optional[StrategicArbitrator] = None,
            resource_manager: Optional[StrategicResourceManager] = None,
            priority_service: Optional[StrategicPriorityService] = None,
            budget_backend: Optional[BudgetPersistenceBackend] = None,
            budget_ledger: Optional[BudgetLedger] = None,
            adapter_registry: Optional[ExecutionAdapterRegistry] = None,
            observer: Optional[StrategicObserver] = None,
            governance_service: Optional[GovernanceService] = None,
            memory_store: Optional[MemoryStore] = None,
            memory_id_source: Optional[MemoryIdSource] = None,
            temporal_analyzer: Optional[TemporalMemoryAnalyzer] = None,
            signal_builder: Optional[MemorySignalBuilder] = None,
            memory_strategy_adapter: Optional[MemoryStrategyAdapter] = None,
            memory_scope_resolver: Optional[MemoryScopeResolver] = None,
            counterfactual_store: Optional[CounterfactualMemoryStore] = None,
            counterfactual_analyzer: Optional[CounterfactualAnalyzer] = None,  # [NEW] Added parameter
            learning_extractor: Optional[LearningExtractor] = None,
            learning_policy_adapter: Optional[LearningPolicyAdapter] = None,
            meta_learning_resolver: Optional[MetaLearningResolver] = None,
            meta_learning_policy: Optional[MetaLearningPolicy] = None
    ):
        self.time_source = time_source
        self.ledger = ledger
        self.backend = backend
        self.profile = profile or RuntimeProfile.dev()
        self.routing_policy = routing_policy or DefaultRoutingPolicy()
        self.arbitrator = arbitrator or PriorityArbitrator()
        self.resource_manager = resource_manager or StrategicResourceManager()
        self.priority_service = priority_service or StrategicPriorityService()
        self.budget_backend = budget_backend or InMemoryBudgetBackend()
        self.budget_ledger = budget_ledger or InMemoryBudgetLedger()
        self.budget_reducer = BudgetReplayReducer()
        self.adapter_registry = adapter_registry or ExecutionAdapterRegistry()
        self.observer = observer or NullStrategicObserver()
        self.governance_service = governance_service
        self.governance_provider = GovernanceRuntimeProvider(
            self.governance_service) if self.governance_service else None

        self.governance_execution_resolver = StandardGovernanceExecutionResolver()
        self.governance_autonomy_resolver = StandardGovernanceAutonomyResolver()
        self.governance_policy_resolver = StandardGovernancePolicyResolver()

        self.memory_store = memory_store or MemoryStore()
        self.memory_ingestion = MemoryIngestionService(self.memory_store)
        self.memory_query = MemoryQueryService(self.memory_store)
        self.memory_id_source = memory_id_source or SystemMemoryIdSource()

        self.temporal_analyzer = temporal_analyzer or TemporalMemoryAnalyzer(LinearDecay(3600))
        self.signal_builder = signal_builder or MemorySignalBuilder()
        self.memory_strategy_adapter = memory_strategy_adapter or MemoryStrategyAdapter()
        self.memory_scope_resolver = memory_scope_resolver or MemoryScopeResolver(self.memory_store)

        self.counterfactual_store = counterfactual_store or CounterfactualMemoryStore()
        self.counterfactual_analyzer = counterfactual_analyzer or CounterfactualAnalyzer()  # [FIXED] Use injected or default

        self.learning_extractor = learning_extractor or LearningExtractor()
        self.learning_policy_adapter = learning_policy_adapter or LearningPolicyAdapter()

        self.meta_learning_resolver = meta_learning_resolver or MetaLearningResolver()
        self.meta_learning_policy = meta_learning_policy or MetaLearningPolicy.default()

        self._ticks_since_failure = 100

        self._runtimes: Dict[str, StrategicContextRuntime] = {}
        self._last_executed_intent: Optional[ExecutionIntent] = None
        self._last_execution_result: Optional[ExecutionResult] = None

        # Initialize Budget (Event Sourced)
        self._budget = self._restore_budget()

        # Enforce Profile Constraints
        if self.profile.env == Environment.REPLAY:
            self.runtime_phase = RuntimePhase.REPLAY
        else:
            self.runtime_phase = RuntimePhase.EXECUTION

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
        # Safety Limit Check
        total_delta = sum(abs(v) for v in delta.values())
        if total_delta > self.profile.limits.max_budget_delta_per_tick:
            msg = f"Budget delta {total_delta} exceeds limit {self.profile.limits.max_budget_delta_per_tick}"
            if self.profile.fail_fast:
                raise SafetyLimitExceeded(msg)
            else:
                self.observer.on_telemetry(
                    TelemetryEvent(now, "SAFETY_VIOLATION", "Orchestrator", payload={"error": msg}))
                return

        event = BudgetEvent(
            id=uuid4(),
            timestamp=now,
            event_type=event_type,
            delta=delta,
            reason=reason
        )
        self.budget_ledger.record(event)
        self._budget = self.budget_reducer.reduce(self._budget, event)

        is_replay = (self.runtime_phase == RuntimePhase.REPLAY)
        self.observer.on_budget_event(event, is_replay=is_replay)

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

        replay_engine = StrategicReplayEngine(
            self.backend, self.ledger, self.time_source
        )

        lifeloop = LifeLoop(
            time_source=self.time_source,
            ledger=self.ledger,
            state_backend=self.backend,
            replay_engine=replay_engine,
            observer=self.observer
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

    def set_phase(self, phase: RuntimePhase) -> None:
        self.runtime_phase = phase

    def tick(self, human: AIHuman, signals: LifeSignals) -> Optional[ExecutionIntent]:
        now = self.time_source.now()
        is_replay = (self.runtime_phase == RuntimePhase.REPLAY)

        self.observer.on_telemetry(TelemetryEvent(now, "TICK_START", "Orchestrator", is_replay=is_replay))

        try:
            # 0. Fetch Governance Context
            governance_context = None
            if self.governance_provider:
                governance_context = self.governance_provider.get_context()

            # 1. Recover Resources
            recovery_delta = self.resource_manager.calculate_recovery_delta(self._budget, now)
            if any(v > 0 for v in recovery_delta.values()):
                self._emit_budget_event("BUDGET_RECOVERED", recovery_delta, "Time-based recovery", now)

            # 2. Inject Feedback
            if self._last_execution_result:
                signals.execution_feedback = self._last_execution_result
                self._last_execution_result = None

                # Update failure tracker
                if signals.execution_feedback.status in (ExecutionStatus.FAILED, ExecutionStatus.REJECTED):
                    self._ticks_since_failure = 0
                else:
                    self._ticks_since_failure += 1
            else:
                self._ticks_since_failure += 1

            # 3. Route Signals
            available_contexts = [r.context for r in self._runtimes.values() if r.active]
            target_contexts = self.routing_policy.resolve(signals, available_contexts)

            candidates: List[Tuple[StrategicContextRuntime, ExecutionIntent, float]] = []
            runtimes_with_intent = set()

            context_analysis_results = {}

            # 4. Tick LifeLoops & Analyze Memory
            for context in target_contexts:
                key = str(context)
                runtime = self._runtimes.get(key)
                if not runtime:
                    continue

                if runtime.tick_count >= self.profile.limits.max_ticks:
                    if self.profile.fail_fast:
                        raise SafetyLimitExceeded(f"Context {key} exceeded max ticks {self.profile.limits.max_ticks}")
                    continue

                # A. Resolve Scoped Memory
                scoped_view = self.memory_scope_resolver.resolve(context)
                scoped_counterfactuals = self.counterfactual_store.list_by_context(context.domain)

                # B. Analyze Scoped Memory
                recent_events = scoped_view.events[-50:]
                weighted_events = self.temporal_analyzer.analyze(recent_events, now)

                recent_counterfactuals = scoped_counterfactuals[-50:]
                cf_metrics = self.counterfactual_analyzer.analyze(recent_counterfactuals, now)

                memory_signal = self.signal_builder.build(weighted_events, self.temporal_analyzer, cf_metrics)
                memory_context = self.memory_strategy_adapter.adapt(memory_signal)

                context_analysis_results[key] = {
                    "memory_signal": memory_signal,
                    "recent_events": recent_events,
                    "recent_counterfactuals": recent_counterfactuals
                }

                # C. Tick LifeLoop
                runtime.tick_count += 1
                internal_context = runtime.lifeloop.tick(
                    human=human,
                    signals=signals,
                    strategic_context=context,
                    tick_count=runtime.tick_count,
                    last_executed_intent=self._last_executed_intent,
                    # governance_context=governance_context
                )

                if internal_context.execution_intent:
                    intent = internal_context.execution_intent
                    if intent.estimated_cost:
                        # D. Filter by Memory Context (Cooldown)
                        if memory_context.cooldown_required:
                            if intent.risk_level > 0.1:
                                runtime.lifeloop.suppress_pending_intentions(human)
                                self._record_counterfactual(intent, "Memory Cooldown", "Memory", governance_context,
                                                            context, now)
                                continue

                        # E. Budget Check
                        allocation = self.resource_manager.evaluate(intent, self._budget)
                        if allocation.approved:
                            # F. Compute Priority (Memory Aware)
                            priority = self.priority_service.compute_priority(intent, runtime, memory_context)
                            candidates.append((runtime, intent, priority))
                            runtimes_with_intent.add(key)
                        else:
                            runtime.lifeloop.suppress_pending_intentions(human)
                            self._record_counterfactual(intent, "Budget Insufficient", "Budget", governance_context,
                                                        context, now)

            # 5. Arbitrate
            winner_intent: Optional[ExecutionIntent] = None
            winner_runtime: Optional[StrategicContextRuntime] = None

            if candidates:
                winner = self.arbitrator.select(candidates)
                if winner:
                    winner_runtime, winner_intent = winner

                    # 7. Governance Execution Gate
                    if governance_context:
                        gate_decision = ExecutionGateDecision.ALLOW
                        final_gate = self.governance_execution_resolver.apply(gate_decision, governance_context)

                        if final_gate == ExecutionGateDecision.DENY:
                            self._record_counterfactual(winner_intent, "Governance Execution Gate", "Governance",
                                                        governance_context, winner_runtime.context, now)
                            winner_intent = None
                            winner_runtime = None

                    if winner_intent:
                        # 8. Reserve Budget
                        if winner_intent.estimated_cost:
                            reservation_delta = self.resource_manager.calculate_reservation_delta(
                                winner_intent.estimated_cost)
                            self._emit_budget_event("BUDGET_RESERVED", reservation_delta,
                                                    f"Reservation for {winner_intent.id}", now)
                            self._last_executed_intent = winner_intent

                            # 9. Execute (External)
                            if self.profile.allow_execution and self.runtime_phase != RuntimePhase.REPLAY:
                                execution_result = self.adapter_registry.execute_safe(winner_intent)
                                self._last_execution_result = execution_result

                                self.observer.on_execution_result(execution_result, is_replay=False)

                                # 10. Commit/Rollback Budget
                                if execution_result.status in (ExecutionStatus.FAILED, ExecutionStatus.REJECTED):
                                    rollback_delta = {k: -v for k, v in reservation_delta.items()}
                                    self._emit_budget_event("BUDGET_ROLLED_BACK", rollback_delta,
                                                            f"Rollback for {winner_intent.id}: {execution_result.status.name}",
                                                            now)
                            else:
                                execution_result = None
                                pass

                            # 11. Memory Ingestion
                            if execution_result:
                                gov_snapshot = GovernanceSnapshot.from_context(
                                    governance_context) if governance_context else GovernanceSnapshot.empty()
                                captured_autonomy = AutonomyState(AutonomyMode.SILENT, "No winner", 0.0, [], False)
                                captured_policy = PolicyDecision(False, "No winner", [])

                                event_record = EventRecord(
                                    id=self.memory_id_source.new_id(),
                                    intent_id=winner_intent.id,
                                    execution_status=execution_result.status,
                                    execution_result=execution_result,
                                    autonomy_state_before=captured_autonomy,
                                    policy_decision=captured_policy,
                                    governance_snapshot=gov_snapshot,
                                    issued_at=now,
                                    context_domain=winner_runtime.context.domain
                                )
                                self.memory_ingestion.ingest(event_record)

                        else:
                            winner_intent = None
                            winner_runtime = None

            # 12. Suppress Losers
            for runtime, intent, _ in candidates:
                if runtime != winner_runtime:
                    runtime.lifeloop.suppress_pending_intentions(human)
                    self._record_counterfactual(intent, "Lost Arbitration", "Arbitration", governance_context,
                                                runtime.context, now)

            # 13. Update Starvation
            for key, runtime in self._runtimes.items():
                if not runtime.active: continue
                is_winner = (runtime == winner_runtime)
                has_intent = (key in runtimes_with_intent)
                runtime.starvation_score = self.priority_service.update_starvation(runtime, is_winner, has_intent)
                if is_winner: runtime.last_win_tick = runtime.tick_count

            # 14. Strategic Learning Loop (Post-Execution)
            aggregated_learning_signal = None

            learning_signals = []
            for key, analysis in context_analysis_results.items():
                signal = self.learning_extractor.extract(
                    analysis["memory_signal"],
                    analysis["recent_events"],
                    analysis["recent_counterfactuals"]
                )
                learning_signals.append(signal)

            if learning_signals:
                avoid_risk = any(s.avoid_risk_patterns for s in learning_signals)
                reduce_expl = any(s.reduce_exploration for s in learning_signals)
                policy_press = any(s.policy_pressure_high for s in learning_signals)
                gov_deadlock = any(s.governance_deadlock_detected for s in learning_signals)
                avg_bias = sum(s.long_term_priority_bias for s in learning_signals) / len(learning_signals)

                raw_signal = StrategicLearningSignal(
                    avoid_risk_patterns=avoid_risk,
                    reduce_exploration=reduce_expl,
                    policy_pressure_high=policy_press,
                    governance_deadlock_detected=gov_deadlock,
                    long_term_priority_bias=avg_bias
                )

                is_gov_locked = False
                if governance_context:
                    is_gov_locked = governance_context.is_autonomy_locked or governance_context.is_execution_locked

                is_stable = True
                for key, analysis in context_analysis_results.items():
                    if analysis["memory_signal"].instability_detected:
                        is_stable = False
                        break

                meta_context = MetaLearningContext(
                    policy=self.meta_learning_policy,
                    is_governance_locked=is_gov_locked,
                    is_system_stable=is_stable,
                    ticks_since_last_failure=self._ticks_since_failure
                )

                aggregated_learning_signal = self.meta_learning_resolver.resolve(raw_signal, meta_context)

            if aggregated_learning_signal:
                current_posture = human.strategy
                new_posture = self.learning_policy_adapter.adapt_posture(current_posture, aggregated_learning_signal)

                if new_posture != current_posture:
                    human.strategy = new_posture
                    # No event emission here per M.6 FIX requirements

            # 15. Persist Budget
            self._persist_budget(now)

            self.observer.on_telemetry(TelemetryEvent(now, "TICK_END", "Orchestrator", payload={
                "winner": str(winner_intent.id) if winner_intent else None}, is_replay=is_replay))

            return winner_intent

        except Exception as e:
            if self.profile.fail_fast:
                raise PanicMode(f"Critical failure in Orchestrator: {e}") from e
            else:
                self.observer.on_telemetry(
                    TelemetryEvent(now, "CRITICAL_ERROR", "Orchestrator", payload={"error": str(e)},
                                   is_replay=is_replay))
                return None

    def _record_counterfactual(
            self,
            intent: ExecutionIntent,
            reason: str,
            stage: str,
            gov_context: Optional[RuntimeGovernanceContext],
            context: StrategicContext,
            now: datetime
    ):
        gov_snapshot = GovernanceSnapshot.from_context(gov_context) if gov_context else GovernanceSnapshot.empty()

        event = CounterfactualEvent(
            id=self.memory_id_source.new_id(),
            intent_id=intent.id,
            intent=intent,
            reason=reason,
            suppression_stage=stage,
            policy_decision=None,
            governance_snapshot=gov_snapshot,
            context_domain=context.domain,
            timestamp=now
        )
        self.counterfactual_store.append(event)