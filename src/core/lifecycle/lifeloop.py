from datetime import datetime
from src.core.domain.entity import AIHuman
from src.core.lifecycle.signals import LifeSignals
from src.core.context.internal import InternalContext

class LifeLoop:
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
            world_perception=None
        )

        return context