from datetime import datetime
from uuid import uuid4
from src.core.domain.entity import AIHuman
from src.core.domain.intention import Intention, DeferredAction
from src.core.lifecycle.signals import LifeSignals
from src.core.context.internal import InternalContext
from src.core.services.impulse import ImpulseGenerator
from src.core.services.intention_gate import IntentionGate
from src.core.services.intention_decay import IntentionDecayService
from src.core.services.intention_pressure import IntentionPressureService
from src.core.services.strategy_filter import StrategicFilterService


class LifeLoop:
    def __init__(self):
        self.impulse_generator = ImpulseGenerator()
        self.intention_gate = IntentionGate()
        self.intention_decay = IntentionDecayService()
        self.intention_pressure = IntentionPressureService()
        self.strategy_filter = StrategicFilterService()

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

        # 5. Build InternalContext
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
            stance_snapshot=stance_snapshot
        )

        # 6. Physics of Volition (Impulse -> Intention)
        candidates = self.impulse_generator.generate(context, now)

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

        # 7. Strategic Filtering (The Cold Veto)
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
                # Silently drop
                pass

        human.intentions = final_intentions

        return context