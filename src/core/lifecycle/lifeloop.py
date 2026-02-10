import random
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import uuid4

from core.interfaces.strategic_memory_store import StrategicMemoryStore
from core.interfaces.strategic_trajectory_memory_store import StrategicTrajectoryMemoryStore
from src.core.context.internal import InternalContext
from src.core.domain.commitment import ExecutionCommitment
from src.core.domain.entity import AIHuman
from src.core.domain.execution_binding import ExecutionBindingSnapshot
from src.core.domain.execution_intent import ExecutionIntent
from src.core.domain.execution_result import ExecutionStatus, ExecutionFailureType
from src.core.domain.intention import Intention
from src.core.domain.persona import PersonaMask
from src.core.domain.strategic_context import StrategicContext
from src.core.domain.strategic_memory import StrategicMemory
from src.core.domain.strategic_snapshot import StrategicSnapshot
from src.core.domain.strategic_trajectory import StrategicTrajectoryMemory, TrajectoryStatus
from src.core.domain.strategy import StrategicPosture, StrategicMode
from src.core.domain.window import ExecutionWindow
from src.core.domain.window_decay import WindowDecayOutcome
from src.core.ledger.in_memory_ledger import InMemoryStrategicLedger
from src.core.ledger.strategic_event import StrategicEvent
from src.core.ledger.strategic_ledger import StrategicLedger
from src.core.lifecycle.signals import LifeSignals
from src.core.observability.null_observer import NullStrategicObserver
from src.core.observability.strategic_observer import StrategicObserver
from src.core.persistence.in_memory_backend import InMemoryStrategicStateBackend
from src.core.persistence.snapshot_policy import SnapshotPolicy, DefaultSnapshotPolicy
from src.core.persistence.strategic_state_backend import StrategicStateBackend
from src.core.persistence.strategic_state_bundle import StrategicStateBundle
from src.core.replay.strategic_replay_engine import StrategicReplayEngine
from src.core.services.commitment import CommitmentEvaluator
from src.core.services.execution_binding import ExecutionBindingService
from src.core.services.execution_eligibility import ExecutionEligibilityService
from src.core.services.horizon_shift import HorizonShiftService
from src.core.services.impulse import ImpulseGenerator
from src.core.services.intention_decay import IntentionDecayService
from src.core.services.intention_gate import IntentionGate
from src.core.services.intention_pressure import IntentionPressureService
from src.core.services.path_key import extract_path_key
from src.core.services.resolution import CommitmentResolutionService
from src.core.services.strategic_interpreter import StrategicFeedbackInterpreter
from src.core.services.strategic_reflection import StrategicReflectionService
from src.core.services.strategic_trajectory import StrategicTrajectoryService
from src.core.services.strategy_adaptation import StrategyAdaptationService
from src.core.services.strategy_filter import StrategicFilterService
from src.core.services.trajectory_rebinding import TrajectoryRebindingService
from src.core.services.window_decay import ExecutionWindowDecayService
from src.core.time.system_time_source import SystemTimeSource
from src.core.time.time_source import TimeSource


@dataclass
class FeedbackModulation:
    readiness_accumulation_factor: float = 1.0
    readiness_decay_factor: float = 1.0
    intention_decay_factor: float = 1.0
    pressure_factor: float = 1.0


class InMemoryStrategicMemoryStore(StrategicMemoryStore):
    def __init__(self):
        self._store: Dict[str, StrategicMemory] = {}

    def load(self, context: StrategicContext) -> StrategicMemory:
        key = str(context)
        return self._store.get(key, StrategicMemory())

    def save(self, context: StrategicContext, memory: StrategicMemory) -> None:
        key = str(context)
        self._store[key] = memory


class InMemoryStrategicTrajectoryMemoryStore(StrategicTrajectoryMemoryStore):
    def __init__(self):
        self._store: Dict[str, StrategicTrajectoryMemory] = {}

    def load(self, context: StrategicContext) -> StrategicTrajectoryMemory:
        key = str(context)
        return self._store.get(key, StrategicTrajectoryMemory())

    def save(self, context: StrategicContext, memory: StrategicTrajectoryMemory) -> None:
        key = str(context)
        self._store[key] = memory


class LifeLoop:
    def __init__(
            self,
            time_source: Optional[TimeSource] = None,
            ledger: Optional[StrategicLedger] = None,
            observer: Optional[StrategicObserver] = None,
            state_backend: Optional[StrategicStateBackend] = None,
            snapshot_policy: Optional[SnapshotPolicy] = None,
            replay_engine: Optional[StrategicReplayEngine] = None  # [NEW] Injected
    ):
        self.time_source = time_source or SystemTimeSource()
        self.ledger = ledger or InMemoryStrategicLedger()
        self.observer = observer or NullStrategicObserver()
        self.state_backend = state_backend or InMemoryStrategicStateBackend()
        self.snapshot_policy = snapshot_policy or DefaultSnapshotPolicy()

        # Replay Engine is now injected or created with dependencies
        self.replay_engine = replay_engine or StrategicReplayEngine(
            self.state_backend, self.ledger, self.time_source
        )

        self.impulse_generator = ImpulseGenerator()
        self.intention_gate = IntentionGate()
        self.intention_decay = IntentionDecayService()
        self.intention_pressure = IntentionPressureService()
        self.strategy_filter = StrategicFilterService()
        self.eligibility_service = ExecutionEligibilityService()
        self.commitment_evaluator = CommitmentEvaluator()
        self.window_decay_service = ExecutionWindowDecayService()
        self.resolution_service = CommitmentResolutionService()
        self.binding_service = ExecutionBindingService()
        self.strategic_interpreter = StrategicFeedbackInterpreter()
        self.strategy_adaptation = StrategyAdaptationService()
        self.strategic_trajectory_service = StrategicTrajectoryService()
        self.horizon_shift_service = HorizonShiftService()
        self.strategic_reflection_service = StrategicReflectionService()
        self.trajectory_rebinding_service = TrajectoryRebindingService()

        self.strategic_memory_store = InMemoryStrategicMemoryStore()
        self.strategic_trajectory_memory_store = InMemoryStrategicTrajectoryMemoryStore()

        self._current_window: Optional[ExecutionWindow] = None
        self._tick_count = 0

    def restore(self, human: AIHuman, context: StrategicContext) -> None:
        """
        Restores strategic state from backend before first tick.
        Delegates entirely to StrategicReplayEngine.
        """
        # 1. Replay Engine reconstructs state from snapshot + events
        bundle = self.replay_engine.restore(context)

        # 2. Apply restored state to runtime components
        human.strategy = bundle.posture
        self.strategic_memory_store.save(context, bundle.memory)
        self.strategic_trajectory_memory_store.save(context, bundle.trajectory_memory)

    def _emit_event(self, event_type: str, details: Dict[str, Any], context: StrategicContext,
                    now: datetime) -> StrategicEvent:
        event = StrategicEvent(
            id=uuid4(),
            timestamp=now,
            event_type=event_type,
            details=details,
            context=context
        )
        self.ledger.record(event)
        self.observer.on_event(event)
        return event

    def _serialize_for_event(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, (StrategicMode, TrajectoryStatus)):
            return obj.value
        if hasattr(obj, "__dataclass_fields__"):
            return {k: self._serialize_for_event(v) for k, v in asdict(obj).items()}
        if isinstance(obj, list):
            return [self._serialize_for_event(i) for i in obj]
        return obj

    def _persist_state(
            self,
            context: StrategicContext,
            posture: StrategicPosture,
            memory: StrategicMemory,
            trajectory_memory: StrategicTrajectoryMemory,
            last_event: Optional[StrategicEvent],
            snapshot: Optional[StrategicSnapshot] = None
    ):
        bundle = StrategicStateBundle(
            posture=posture,
            memory=memory,
            trajectory_memory=trajectory_memory,
            last_snapshot=snapshot,
            last_event_id=last_event.id if last_event else None,
            version="1.1"
        )
        self.state_backend.save(context, bundle)

    def get_strategic_snapshot(self, human: AIHuman, context: StrategicContext) -> StrategicSnapshot:
        traj_mem = self.strategic_trajectory_memory_store.load(context)
        mem = self.strategic_memory_store.load(context)

        active = [t for t in traj_mem.trajectories.values() if t.status == TrajectoryStatus.ACTIVE]
        stalled = [t for t in traj_mem.trajectories.values() if t.status == TrajectoryStatus.STALLED]
        abandoned = [t for t in traj_mem.trajectories.values() if t.status == TrajectoryStatus.ABANDONED]

        path_statuses = {str(k): v for k, v in mem.paths.items()}

        return StrategicSnapshot(
            mode=human.strategy.mode,
            horizon_days=human.strategy.horizon_days,
            confidence=human.strategy.confidence_baseline,
            risk_tolerance=human.strategy.risk_tolerance,
            persistence_factor=human.strategy.persistence_factor,
            active_trajectories=active,
            stalled_trajectories=stalled,
            abandoned_trajectories=abandoned,
            path_statuses=path_statuses
        )

    def _select_mask(self, human: AIHuman) -> Optional[PersonaMask]:
        if not human.personas:
            return None
        return random.choice(human.personas)

    def _calculate_feedback_modulation(self, signals: LifeSignals) -> FeedbackModulation:
        mod = FeedbackModulation()
        if not signals.execution_feedback:
            return mod
        feedback = signals.execution_feedback
        if feedback.status == ExecutionStatus.SUCCESS:
            mod.readiness_accumulation_factor = 0.5
            mod.readiness_decay_factor = 2.0
            mod.intention_decay_factor = 2.0
        elif feedback.status == ExecutionStatus.FAILED:
            if feedback.failure_type == ExecutionFailureType.ENVIRONMENT:
                mod.readiness_accumulation_factor = 1.2
                mod.readiness_decay_factor = 0.5
                mod.intention_decay_factor = 0.5
            elif feedback.failure_type == ExecutionFailureType.INTERNAL:
                mod.readiness_accumulation_factor = 0.9
        elif feedback.status == ExecutionStatus.REJECTED:
            if feedback.failure_type == ExecutionFailureType.POLICY:
                mod.readiness_accumulation_factor = 0.8
                mod.readiness_decay_factor = 1.2
        elif feedback.status == ExecutionStatus.PARTIAL:
            mod.readiness_decay_factor = 1.5
            mod.intention_decay_factor = 1.5
        return mod

    def tick(
            self,
            human: AIHuman,
            signals: LifeSignals,
            strategic_context: StrategicContext,
            tick_count: int,
            existing_window: Optional[ExecutionWindow] = None,
            existing_commitment: Optional[ExecutionCommitment] = None,
            last_executed_intent: Optional[ExecutionIntent] = None
    ) -> InternalContext:

        now = self.time_source.now()

        # 1. Update State
        human.state.set_resting(signals.rest)

        if signals.energy_delta < 0 or signals.attention_delta < 0:
            human.state.apply_cost(abs(signals.energy_delta), abs(signals.attention_delta))
        else:
            human.state.recover(signals.energy_delta, signals.attention_delta)
        for topic, (p, s) in signals.perceived_topics.items():
            human.stance.update_topic(topic, p, s, now)
        for m in signals.memories:
            human.memory.add_short(m)

        # 2. Calculate Feedback Modulation & Strategic Adaptation
        modulation = self._calculate_feedback_modulation(signals)

        current_memory = self.strategic_memory_store.load(strategic_context)
        current_trajectory_memory = self.strategic_trajectory_memory_store.load(strategic_context)

        last_event: Optional[StrategicEvent] = None

        if signals.execution_feedback and last_executed_intent:
            strategic_signals = self.strategic_interpreter.interpret(
                signals.execution_feedback
            )

            if not hasattr(human, 'strategy'):
                human.strategy = StrategicPosture([], 0.5, 0.5, 1.0, StrategicMode.BALANCED)

            # A. Adapt Strategy & Memory
            new_posture, new_memory = self.strategy_adaptation.adapt(
                human.strategy,
                current_memory,
                strategic_signals,
                last_executed_intent,
                strategic_context,
                now
            )

            if new_posture != human.strategy:
                last_event = self._emit_event(
                    "STRATEGY_ADAPTATION",
                    {"posture_after": self._serialize_for_event(new_posture)},
                    strategic_context,
                    now
                )

            # Check for memory changes (Path Abandonment)
            path_key = extract_path_key(last_executed_intent, strategic_context)
            old_status = current_memory.get_status(path_key)
            new_status = new_memory.get_status(path_key)

            if old_status != new_status:
                last_event = self._emit_event(
                    "PATH_ABANDONMENT",
                    {
                        "path_key": list(path_key),
                        "path_status_after": self._serialize_for_event(new_status)
                    },
                    strategic_context,
                    now
                )

            # B. Update Trajectories
            new_trajectory_memory = self.strategic_trajectory_service.update(
                current_trajectory_memory,
                strategic_signals,
                last_executed_intent,
                strategic_context,
                new_posture,
                now
            )

            # Detect trajectory changes
            for t_id, t_new in new_trajectory_memory.trajectories.items():
                t_old = current_trajectory_memory.get_trajectory(t_id)
                if t_old != t_new:
                    last_event = self._emit_event(
                        "TRAJECTORY_UPDATE",
                        {
                            "trajectory_id": t_id,
                            "trajectory_after": self._serialize_for_event(t_new)
                        },
                        strategic_context,
                        now
                    )

            # C. Strategic Reflection
            reflections = self.strategic_reflection_service.reflect(
                new_trajectory_memory,
                new_memory,
                new_posture,
                strategic_context,
                now
            )

            for r in reflections:
                last_event = self._emit_event("REFLECTION", {"trajectory": r.trajectory_id, "outcome": r.outcome.value},
                                              strategic_context, now)

            # D. Trajectory Rebinding
            final_trajectory_memory, rebindings = self.trajectory_rebinding_service.rebind(
                new_trajectory_memory,
                reflections,
                new_posture,
                now
            )

            for rb in rebindings:
                source_after = final_trajectory_memory.get_trajectory(rb.source_trajectory_id)
                target_after = final_trajectory_memory.get_trajectory(rb.target_trajectory_id)

                last_event = self._emit_event(
                    "REBINDING",
                    {
                        "source_trajectory_after": self._serialize_for_event(source_after),
                        "target_trajectory_after": self._serialize_for_event(target_after)
                    },
                    strategic_context,
                    now
                )

            # E. Horizon Shift
            final_posture = self.horizon_shift_service.evaluate(
                new_posture,
                new_memory,
                now
            )

            if final_posture.mode != new_posture.mode:
                last_event = self._emit_event(
                    "HORIZON_SHIFT",
                    {"posture_after": self._serialize_for_event(final_posture)},
                    strategic_context,
                    now
                )

            human.strategy = final_posture
            self.strategic_memory_store.save(strategic_context, new_memory)
            self.strategic_trajectory_memory_store.save(strategic_context, final_trajectory_memory)

            current_memory = new_memory
            current_trajectory_memory = final_trajectory_memory

        # Persistence Check
        if self.snapshot_policy.should_save(strategic_context, tick_count, last_event, human.strategy):
            self._persist_state(strategic_context, human.strategy, current_memory, current_trajectory_memory,
                                last_event)

        # 3. Intention Decay
        surviving_intentions = []
        total_intentions = len(human.intentions)
        for intention in human.intentions:
            updated_intention = self.intention_decay.evaluate(
                intention, human.state, human.readiness, total_intentions, now, modulation.intention_decay_factor
            )
            if updated_intention:
                surviving_intentions.append(updated_intention)
        human.intentions = surviving_intentions

        # 4. Intention Pressure
        pressure_delta = self.intention_pressure.calculate_pressure(human.intentions, human.state)

        # 5. Update Readiness
        total_pressure = signals.pressure_delta + pressure_delta
        if total_pressure > 0:
            human.readiness.accumulate(total_pressure * modulation.readiness_accumulation_factor)
        else:
            base_decay = abs(total_pressure) if total_pressure < 0 else 2.0
            human.readiness.decay(base_decay * modulation.readiness_decay_factor)

        # 6. Physics of Volition
        temp_stance_snapshot = {t: s.intensity for t, s in human.stance.topics.items()}
        temp_context = InternalContext(
            human.identity.name, "neutral",
            "high" if human.state.energy > 70 else "moderate" if human.state.energy > 30 else "low",
            human.memory.recent(5), len(human.intentions), human.readiness.level(), human.readiness.value, None,
            temp_stance_snapshot
        )
        candidates = self.impulse_generator.generate(temp_context, now)
        for candidate in candidates:
            if self.intention_gate.allow(candidate, human.state):
                new_intention = Intention(
                    uuid4(), "generated", f"Focus on {candidate.topic}", float(candidate.pressure / 10.0),
                    now, 3600, {"origin": "impulse", "topic": candidate.topic}
                )
                human.intentions.append(new_intention)
                human.state.apply_cost(5.0, 2.0)

        # 7. Strategic Filtering
        final_intentions = []
        if not hasattr(human, 'strategy'): human.strategy = StrategicPosture([], 0.5, 0.5, 1.0, StrategicMode.BALANCED)
        for intention in human.intentions:
            decision = self.strategy_filter.evaluate(intention, human.strategy, current_memory,
                                                     current_trajectory_memory, strategic_context, now)
            if decision.allow: final_intentions.append(intention)
        human.intentions = final_intentions

        # 8. Execution Window Logic
        decay_result = None
        active_window = None
        active_commitment = existing_commitment
        if not active_commitment:
            if existing_window:
                decay_result = self.window_decay_service.evaluate(existing_window, human.state, human.readiness, now)
                if decay_result.outcome == WindowDecayOutcome.PERSIST:
                    active_window = existing_window
                else:
                    active_window = None

            eligibility_map = {}
            if not active_window:
                mask = self._select_mask(human)
                if mask:
                    sorted_intentions = sorted(human.intentions, key=lambda x: x.priority, reverse=True)
                    for intention in sorted_intentions:
                        eligibility = self.eligibility_service.evaluate(intention, mask, human.state, human.readiness,
                                                                        None, now)
                        eligibility_map[intention.id] = eligibility
                        if eligibility.allow and active_window is None:
                            new_window = self.commitment_evaluator.evaluate(intention, eligibility, mask, human.state,
                                                                            human.readiness, now)
                            if new_window: active_window = new_window

            if active_window:
                resolution_result = self.resolution_service.resolve(active_window, human.state, human.readiness, now)
                if resolution_result.commitment:
                    active_commitment = resolution_result.commitment
                    self._emit_event("COMMITMENT_FORMED", {"id": str(active_commitment.id)}, strategic_context, now)
                if resolution_result.window_consumed: active_window = None

        # 9. Execution Binding
        execution_intent = None
        if active_commitment:
            binding_snapshot = ExecutionBindingSnapshot(human.state.energy, human.state.fatigue, human.readiness.value)
            execution_intent = self.binding_service.bind(active_commitment, binding_snapshot, now)

        # 10. Build Final InternalContext
        stance_snapshot = {t: s.intensity for t, s in human.stance.topics.items()}
        context = InternalContext(
            human.identity.name, "neutral",
            "high" if human.state.energy > 70 else "moderate" if human.state.energy > 30 else "low",
            human.memory.recent(5), len(human.intentions), human.readiness.level(), human.readiness.value, None,
            stance_snapshot, eligibility_map if not active_commitment else {}, active_window, decay_result,
            active_commitment, execution_intent
        )

        return context

    def suppress_pending_intentions(self, human: AIHuman) -> None:
        """
        Soft suppression of pending intentions/commitments for non-selected contexts.
        Called by Orchestrator after arbitration.
        """
        if human.readiness.value > 0:
            human.readiness.decay(5.0)