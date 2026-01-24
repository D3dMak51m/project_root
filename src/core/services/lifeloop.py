from datetime import datetime
from src.core.domain.entity import AIHuman
from src.core.domain.context import InternalContext
from src.core.services.thinking import ThinkingService
from src.core.services.internalization import InternalizationService
from src.core.services.opinion import OpinionService
from src.core.services.pressure import PressureService


class LifeLoop:
    def __init__(
            self,
            thinking_service: ThinkingService,
            internalization_service: InternalizationService,
            opinion_service: OpinionService,
            pressure_service: PressureService
    ):
        self.thinking_service = thinking_service
        self.internalization_service = internalization_service
        self.opinion_service = opinion_service
        self.pressure_service = pressure_service

    def tick(self, human: AIHuman, current_time: datetime) -> None:
        # 1. Passive Existence
        human.exist(current_time)

        if human.state.energy < 10.0:
            human.state.set_resting_state(True)
            return

        # 2. Internalization
        perception = self.internalization_service.perceive_world(human)

        # 3. Optional Memory Write
        if perception:
            memory_text = f"I noticed the world feels {perception.dominant_mood}. Topics: {', '.join(perception.interesting_topics)}."
            human.memory.add_short_term(memory_text, importance=0.2)

        # 4. Form Context (Pre-Pressure)
        recent_memories = [m.content for m in human.memory.short_term_buffer[-3:]]

        # We build a temporary context to calculate pressure/opinions
        temp_context = InternalContext.build(
            identity=human.identity,
            state=human.state,
            memories=recent_memories,
            intentions_count=len(human.intentions),
            readiness=human.readiness,  # Current readiness
            world_perception=perception
        )

        # 5. Opinion Formation
        self.opinion_service.form_opinions(human, temp_context)

        # 6. Pressure & Readiness Update [FIXED]
        # Calculate delta
        pressure_delta = self.pressure_service.calculate_delta(human, temp_context)

        # Apply fatigue dampener (LifeLoop logic)
        if human.state.fatigue > 70.0 and pressure_delta > 0:
            pressure_delta *= 0.5  # Reduce accumulation if tired

        # Apply to state
        if pressure_delta > 0:
            human.readiness.accumulate(pressure_delta)
        else:
            human.readiness.decay(abs(pressure_delta))

        # 7. Re-build Context with Updated Readiness & Stance info
        # This ensures Thinking sees the *result* of the pressure update
        relevant_stances = self.opinion_service.get_relevant_stances(human, temp_context)
        final_memories = recent_memories + relevant_stances

        final_context = InternalContext.build(
            identity=human.identity,
            state=human.state,
            memories=final_memories,
            intentions_count=len(human.intentions),
            readiness=human.readiness,  # Updated readiness
            world_perception=perception
        )

        # 8. Thinking Process
        thought_content, new_intention = self.thinking_service.think(final_context, human.identity.name)

        human.state.apply_resource_cost(energy_cost=2.0, attention_cost=5.0)
        human.memory.add_short_term(content=thought_content, importance=0.1)

        if new_intention:
            human.add_intention(new_intention)