from datetime import datetime
from uuid import uuid4, UUID
import random
from typing import Optional, Dict
from dataclasses import dataclass

from src.core.domain.entity import AIHuman
from src.core.domain.intention import Intention, DeferredAction
from src.core.domain.persona import PersonaMask
from src.core.domain.execution import ExecutionEligibilityResult
from src.core.domain.window import ExecutionWindow
from src.core.domain.window_decay import WindowDecayOutcome, ExecutionWindowDecayResult
from src.core.domain.commitment import ExecutionCommitment
from src.core.domain.execution_intent import ExecutionIntent
from src.core.domain.execution_binding import ExecutionBindingSnapshot
from src.core.domain.execution_result import ExecutionStatus, ExecutionFailureType
from src.core.lifecycle.signals import LifeSignals
from src.core.context.internal import InternalContext
from src.core.services.impulse import ImpulseGenerator
from src.core.services.intention_gate import IntentionGate
from src.core.services.intention_decay import IntentionDecayService
from src.core.services.intention_pressure import IntentionPressureService
from src.core.services.strategy_filter import StrategicFilterService
from src.core.services.execution_eligibility import ExecutionEligibilityService
from src.core.services.commitment import CommitmentEvaluator
from src.core.services.window_decay import ExecutionWindowDecayService
from src.core.services.resolution import CommitmentResolutionService
from src.core.services.execution_binding import ExecutionBindingService


@dataclass
class FeedbackModulation:
    readiness_accumulation_factor: float = 1.0
    readiness_decay_factor: float = 1.0
    intention_decay_factor: float = 1.0
    pressure_factor: float = 1.0


class LifeLoop:
    def __init__(self):
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
            now: datetime,
            existing_window: Optional[ExecutionWindow] = None,
            existing_commitment: Optional[ExecutionCommitment] = None
    ) -> InternalContext:
        # 1. Update State
        human.state.set_resting(signals.rest)

        if signals.energy_delta < 0 or signals.attention_delta < 0:
            human.state.apply_cost(
                energy_cost=abs(signals.energy_delta),
                attention_cost=abs(signals.attention_delta)
            )
        else:
            human.state.recover(
                energy_gain=signals.energy_delta,
                attention_gain=signals.attention_delta
            )

        for topic, (pressure, sentiment) in signals.perceived_topics.items():
            human.stance.update_topic(
                topic=topic,
                pressure=pressure,
                sentiment=sentiment,
                now=now
            )

        for m in signals.memories:
            human.memory.add_short(m)

        # 2. Calculate Feedback Modulation (Physics)
        modulation = self._calculate_feedback_modulation(signals)

        # 3. Intention Decay & Inertia
        surviving_intentions = []
        total_intentions = len(human.intentions)

        for intention in human.intentions:
            updated_intention = self.intention_decay.evaluate(
                intention=intention,
                state=human.state,
                readiness=human.readiness,
                total_intentions=total_intentions,
                now=now,
                external_decay_factor=modulation.intention_decay_factor
            )
            if updated_intention:
                surviving_intentions.append(updated_intention)

        human.intentions = surviving_intentions

        # 4. Intention Pressure
        pressure_delta = self.intention_pressure.calculate_pressure(
            human.intentions,
            human.state
        )

        # 5. Update Readiness
        total_pressure = signals.pressure_delta + pressure_delta

        if total_pressure > 0:
            human.readiness.accumulate(total_pressure * modulation.readiness_accumulation_factor)
        else:
            base_decay = abs(total_pressure) if total_pressure < 0 else 2.0
            human.readiness.decay(base_decay * modulation.readiness_decay_factor)

        # 6. Physics of Volition
        temp_stance_snapshot = {
            topic: stance.intensity
            for topic, stance in human.stance.topics.items()
        }
        temp_context = InternalContext(
            identity_summary=human.identity.name,
            current_mood="neutral",
            energy_level="moderate",
            recent_thoughts=[],
            active_intentions_count=len(human.intentions),
            readiness_level=human.readiness.level(),
            readiness_value=human.readiness.value,
            world_perception=None,
            stance_snapshot=temp_stance_snapshot
        )

        candidates = self.impulse_generator.generate(temp_context, now)

        for candidate in candidates:
            if self.intention_gate.allow(candidate, human.state):
                new_intention = Intention(
                    id=uuid4(),
                    type="generated",
                    content=f"Focus on {candidate.topic}",
                    priority=float(candidate.pressure / 10.0),
                    created_at=now,
                    ttl_seconds=3600,
                    metadata={"origin": "impulse", "topic": candidate.topic}
                )
                human.intentions.append(new_intention)
                human.state.apply_cost(energy_cost=5.0, attention_cost=2.0)

        # 7. Strategic Filtering
        final_intentions = []

        for intention in human.intentions:
            decision = self.strategy_filter.evaluate(
                intention,
                human.strategy,
                human.readiness,
                now
            )

            if decision.allow:
                final_intentions.append(intention)
            elif decision.defer:
                deferred = DeferredAction(
                    id=uuid4(),
                    intention_id=intention.id,
                    reason=decision.reason,
                    resume_after=decision.suggested_resume_after or now
                )
                human.deferred_actions.append(deferred)
            elif decision.suppress:
                pass

        human.intentions = final_intentions

        # 8. Execution Window Logic
        decay_result: Optional[ExecutionWindowDecayResult] = None
        active_window: Optional[ExecutionWindow] = None
        active_commitment: Optional[ExecutionCommitment] = existing_commitment

        if not active_commitment:
            if existing_window:
                decay_result = self.window_decay_service.evaluate(
                    window=existing_window,
                    state=human.state,
                    readiness=human.readiness,
                    now=now
                )

                if decay_result.outcome == WindowDecayOutcome.PERSIST:
                    active_window = existing_window
                else:
                    active_window = None

            eligibility_map: Dict[UUID, ExecutionEligibilityResult] = {}

            if not active_window:
                mask = self._select_mask(human)
                if mask:
                    sorted_intentions = sorted(human.intentions, key=lambda x: x.priority, reverse=True)

                    for intention in sorted_intentions:
                        eligibility = self.eligibility_service.evaluate(
                            intention=intention,
                            mask=mask,
                            state=human.state,
                            readiness=human.readiness,
                            reputation=None,
                            now=now
                        )
                        eligibility_map[intention.id] = eligibility

                        if eligibility.allow and active_window is None:
                            new_window = self.commitment_evaluator.evaluate(
                                intention=intention,
                                eligibility=eligibility,
                                mask=mask,
                                state=human.state,
                                readiness=human.readiness,
                                now=now
                            )
                            if new_window:
                                active_window = new_window

            if active_window:
                resolution_result = self.resolution_service.resolve(
                    window=active_window,
                    state=human.state,
                    readiness=human.readiness,
                    now=now
                )

                if resolution_result.commitment:
                    active_commitment = resolution_result.commitment

                if resolution_result.window_consumed:
                    active_window = None

        # 9. Execution Binding (Projection)
        execution_intent: Optional[ExecutionIntent] = None

        if active_commitment:
            binding_snapshot = ExecutionBindingSnapshot(
                energy_value=human.state.energy,
                fatigue_value=human.state.fatigue,
                readiness_value=human.readiness.value
            )

            execution_intent = self.binding_service.bind(
                commitment=active_commitment,
                snapshot=binding_snapshot,
                now=now
            )

        # 10. Build Final InternalContext
        stance_snapshot = {
            topic: stance.intensity
            for topic, stance in human.stance.topics.items()
        }

        context = InternalContext(
            identity_summary=human.identity.name,
            current_mood="neutral",
            energy_level=(
                "high" if human.state.energy > 70
                else "moderate" if human.state.energy > 30
                else "low"
            ),
            recent_thoughts=human.memory.recent(5),
            active_intentions_count=len(human.intentions),
            readiness_level=human.readiness.level(),
            readiness_value=human.readiness.value,
            world_perception=None,
            stance_snapshot=stance_snapshot,
            execution_eligibility=eligibility_map if not active_commitment else {},
            execution_window=active_window,
            last_window_decay=decay_result,
            execution_commitment=active_commitment,
            execution_intent=execution_intent
        )

        return context