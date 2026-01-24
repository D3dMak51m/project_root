from datetime import datetime
from uuid import uuid4
from src.core.domain.entity import AIHuman
from src.core.domain.intention import Intention
from src.core.lifecycle.signals import LifeSignals
from src.core.context.internal import InternalContext
from src.core.services.impulse import ImpulseGenerator
from src.core.services.intention_gate import IntentionGate
from src.core.services.intention_decay import IntentionDecayService


class LifeLoop:
    def __init__(self):
        self.impulse_generator = ImpulseGenerator()
        self.intention_gate = IntentionGate()
        self.intention_decay = IntentionDecayService()

    def tick(
            self,
            human: AIHuman,
            signals: LifeSignals,
            now: datetime
    ) -> InternalContext:
        # 1. Update State (Energy / Fatigue / Memory / Readiness / Stance)
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

        if signals.pressure_delta > 0:
            human.readiness.accumulate(signals.pressure_delta)
        else:
            human.readiness.decay(abs(signals.pressure_delta))

        for m in signals.memories:
            human.memory.add_short(m)

        # 2. Build InternalContext (READ-ONLY SNAPSHOT)
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

        # 3. Generate IntentionCandidates (Physics of Volition)
        candidates = self.impulse_generator.generate(context, now)

        # 4. Crystallize New Intentions
        for candidate in candidates:
            if self.intention_gate.allow(candidate, human.state):
                new_intention = Intention(
                    id=uuid4(),
                    type="generated",
                    content=f"Focus on {candidate.topic}",
                    priority=float(candidate.pressure / 10.0),  # Float priority
                    created_at=now,
                    ttl_seconds=3600,
                    metadata={"origin": "impulse", "topic": candidate.topic}
                )
                human.intentions.append(new_intention)

                # Cost of formation
                human.state.apply_cost(energy_cost=5.0, attention_cost=2.0)

        # 5. Apply IntentionDecay to ALL intentions (old + new)
        # This is the last mutating step for intentions in this tick
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

        # 6. Finalize human.intentions
        human.intentions = surviving_intentions

        # 7. Return InternalContext (Snapshot of state BEFORE decay/formation logic,
        # or should it reflect post-tick state?
        # Per instructions: "return InternalContext" is the last step.
        # The context was built in step 2. We return that snapshot.)
        return context