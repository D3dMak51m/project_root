from datetime import datetime
from uuid import uuid4, UUID
import random
from typing import Optional, Dict

from src.core.domain.entity import AIHuman
from src.core.domain.intention import Intention, DeferredAction
from src.core.domain.persona import PersonaMask
from src.core.domain.execution import ExecutionEligibilityResult
from src.core.lifecycle.signals import LifeSignals
from src.core.context.internal import InternalContext
from src.core.services.impulse import ImpulseGenerator
from src.core.services.intention_gate import IntentionGate
from src.core.services.intention_decay import IntentionDecayService
from src.core.services.intention_pressure import IntentionPressureService
from src.core.services.strategy_filter import StrategicFilterService
from src.core.services.execution_eligibility import ExecutionEligibilityService


class LifeLoop:
    def __init__(self):
        self.impulse_generator = ImpulseGenerator()
        self.intention_gate = IntentionGate()
        self.intention_decay = IntentionDecayService()
        self.intention_pressure = IntentionPressureService()
        self.strategy_filter = StrategicFilterService()
        self.eligibility_service = ExecutionEligibilityService()

    def _select_mask(self, human: AIHuman) -> Optional[PersonaMask]:
        """
        Simple strategy: Pick a random mask or based on some internal logic.
        """
        if not human.personas:
            return None
        return random.choice(human.personas)

    def tick(
            self,
            human: AIHuman,
            signals: LifeSignals,
            now: datetime
    ) -> InternalContext:
        # 1. Update State (Energy / Fatigue / Memory / Stance)
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

        # 2. Intention Decay & Inertia
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

        # 5. Physics of Volition (Impulse -> Intention)
        # We need a temporary context for impulse generation to read readiness/stance
        # This is a lightweight snapshot for internal logic
        temp_stance_snapshot = {
            topic: stance.intensity
            for topic, stance in human.stance.topics.items()
        }
        temp_context = InternalContext(
            identity_summary=human.identity.name,
            current_mood="neutral",
            energy_level="moderate",  # Simplified for temp context
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

        # 7. Compute Execution Eligibility [NEW]
        # Calculated for ALL surviving intentions BEFORE context finalization
        eligibility_map: Dict[UUID, ExecutionEligibilityResult] = {}
        mask = self._select_mask(human)

        if mask:
            for intention in human.intentions:
                result = self.eligibility_service.evaluate(
                    intention=intention,
                    mask=mask,
                    state=human.state,
                    readiness=human.readiness,
                    reputation=None,
                    now=now
                )
                eligibility_map[intention.id] = result

        # 8. Build Final InternalContext (READ-ONLY SNAPSHOT)
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
            execution_eligibility=eligibility_map  # [NEW] Injected into context
        )

        return context