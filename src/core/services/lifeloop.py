from datetime import datetime
from src.core.domain.entity import AIHuman
from src.core.domain.context import InternalContext
from src.core.services.thinking import ThinkingService
from src.core.services.internalization import InternalizationService


class LifeLoop:
    def __init__(self, thinking_service: ThinkingService, internalization_service: InternalizationService):
        self.thinking_service = thinking_service
        self.internalization_service = internalization_service

    def tick(self, human: AIHuman, current_time: datetime) -> None:
        # 1. Passive Existence
        human.exist(current_time)

        if human.state.energy < 10.0:
            human.state.set_resting_state(True)
            return

        # 2. Internalization (Transient)
        # Fetch perception, but do not store it in the human entity yet
        perception = self.internalization_service.perceive_world(human)

        # 3. Optional Memory Write (Decision belongs to LifeLoop logic for now)
        if perception:
            memory_text = f"I noticed the world feels {perception.dominant_mood}. Topics: {', '.join(perception.interesting_topics)}."
            human.memory.add_short_term(memory_text, importance=0.2)

        # 4. Form Internal Context (L3)
        recent_memories = [m.content for m in human.memory.short_term_buffer[-3:]]

        context = InternalContext.build(
            identity=human.identity,
            state=human.state,
            memories=recent_memories,
            intentions_count=len(human.intentions),
            world_perception=perception  # Passed transiently
        )

        # 5. Thinking Process
        thought_content, new_intention = self.thinking_service.think(context, human.identity.name)

        human.state.apply_resource_cost(energy_cost=2.0, attention_cost=5.0)
        human.memory.add_short_term(content=thought_content, importance=0.1)

        if new_intention:
            human.add_intention(new_intention)