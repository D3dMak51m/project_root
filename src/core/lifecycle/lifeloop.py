from datetime import datetime
from uuid import uuid4
from src.core.domain.entity import AIHuman
from src.core.domain.intention import Intention
from src.core.lifecycle.signals import LifeSignals
from src.core.context.internal import InternalContext
from src.core.services.impulse import ImpulseGenerator
from src.core.services.intention_gate import IntentionGate


class LifeLoop:
    def __init__(self):
        self.impulse_generator = ImpulseGenerator()
        self.intention_gate = IntentionGate()

    def tick(
            self,
            human: AIHuman,
            signals: LifeSignals,
            now: datetime
    ) -> InternalContext:
        # 1. Rest flag
        human.state.set_resting(signals.rest)

        # 2. Energy / attention update
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

        # 3. Update stance (opinions)
        for topic, (pressure, sentiment) in signals.perceived_topics.items():
            human.stance.update_topic(
                topic=topic,
                pressure=pressure,
                sentiment=sentiment,
                now=now
            )

        # 4. Update readiness
        if signals.pressure_delta > 0:
            human.readiness.accumulate(signals.pressure_delta)
        else:
            human.readiness.decay(abs(signals.pressure_delta))

        # 5. Update memory
        for m in signals.memories:
            human.memory.add_short(m)

        # 6. Build InternalContext (READ-ONLY SNAPSHOT)
        # Extract stance snapshot for context
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
            stance_snapshot=stance_snapshot  # [NEW] Inject snapshot
        )

        # 7. Physics of Volition (Impulse -> Intention)
        candidates = self.impulse_generator.generate(context, now)

        for candidate in candidates:
            if self.intention_gate.allow(candidate, human.state):
                # Crystallize Intention
                new_intention = Intention(
                    id=uuid4(),
                    type="generated",
                    content=f"Focus on {candidate.topic}",
                    priority=int(candidate.pressure / 10),
                    created_at=now,
                    ttl_seconds=3600,  # Default TTL
                    metadata={"origin": "impulse", "topic": candidate.topic}
                )
                human.intentions.append(new_intention)

                # Cost of formation
                human.state.apply_cost(energy_cost=5.0, attention_cost=2.0)

        return context