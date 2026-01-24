from datetime import datetime
from uuid import uuid4, UUID
import random
from typing import Optional, Dict

from src.core.domain.entity import AIHuman
from src.core.domain.intention import Intention, DeferredAction
from src.core.domain.persona import PersonaMask
from src.core.domain.execution import ExecutionEligibilityResult
from src.core.domain.window import ExecutionWindow
from src.core.domain.window_decay import WindowDecayOutcome, ExecutionWindowDecayResult
from src.core.domain.commitment import ExecutionCommitment
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

    def _select_mask(self, human: AIHuman) -> Optional[PersonaMask]:
        if not human.personas:
            return None
        return random.choice(human.personas)

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

        # 2. Intention Decay
        surviving_intentions = []
        total_intentions = len(human.intentions)

        for intention in human.intentions:
            updated_intention = self.intention_decay.evaluate(
                intention=intention,
                state=human.state,
                readiness=human.readiness,
                total_intentions=total_intentions,
                now=now
            )
            if updated_intention:
                surviving_intentions.append(updated_intention)

        human.intentions = surviving_intentions

        # 3. Intention Pressure
        pressure_delta = self.intention_pressure.calculate_pressure(
            human.intentions,
            human.state
        )

        # 4. Update Readiness
        total_pressure = signals.pressure_delta + pressure_delta

        if total_pressure > 0:
            human.readiness.accumulate(total_pressure)
        else:
            human.readiness.decay(abs(total_pressure) if total_pressure < 0 else 2.0)

        # 5. Physics of Volition
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

        # 6. Strategic Filtering
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

        # 7. Execution Window Logic

        decay_result: Optional[ExecutionWindowDecayResult] = None
        active_window: Optional[ExecutionWindow] = None
        active_commitment: Optional[ExecutionCommitment] = existing_commitment

        if not active_commitment:
            # A. Handle Existing Window (Decay)
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

            # B. Handle New Window (Commitment) - Only if no active window
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

            # C. Commitment Resolution
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

        # 8. Build Final InternalContext
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
            execution_commitment=active_commitment
        )

        return context