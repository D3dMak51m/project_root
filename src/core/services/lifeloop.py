from datetime import datetime
from src.core.domain.entity import AIHuman
from src.core.domain.context import InternalContext
from src.core.services.thinking import ThinkingService
from src.core.services.internalization import InternalizationService
from src.core.services.opinion import OpinionService


class LifeLoop:
    """
    The deterministic driver of the AIHuman.
    It orchestrates the sequence:
    Exist -> Perceive(Internal) -> Opinion -> Think -> Form Intention.
    """

    def __init__(
            self,
            thinking_service: ThinkingService,
            internalization_service: InternalizationService,
            opinion_service: OpinionService
    ):
        self.thinking_service = thinking_service
        self.internalization_service = internalization_service
        self.opinion_service = opinion_service

    def tick(self, human: AIHuman, current_time: datetime) -> None:
        # 1. Passive Existence (Physics of the mind)
        # Updates energy, fatigue, cleans up dead intentions
        human.exist(current_time)

        # 2. Check constraints (Fatigue check)
        # If too tired, force rest or skip thinking
        if human.state.energy < 10.0:
            human.state.set_resting_state(True)
            return

        # 3. Internalization (Perceive the World)
        # This is a PULL operation. It returns a transient perception object.
        # It does NOT trigger thinking directly.
        perception = self.internalization_service.perceive_world(human)

        # 4. Optional Memory Write (Decision belongs to LifeLoop logic)
        if perception:
            memory_text = f"I noticed the world feels {perception.dominant_mood}. Topics: {', '.join(perception.interesting_topics)}."
            human.memory.add_short_term(memory_text, importance=0.2)

        # 5. Form Internal Context (L3)
        # Subjective snapshot of self
        recent_memories = [m.content for m in human.memory.short_term_buffer[-3:]]

        context = InternalContext.build(
            identity=human.identity,
            state=human.state,
            memories=recent_memories,
            intentions_count=len(human.intentions),
            world_perception=perception  # Passed transiently
        )

        # 6. Opinion Formation
        # Evolve stance based on what was just perceived
        self.opinion_service.form_opinions(human, context)

        # 7. Enrich Context with Stance
        # The thinking process should know about strong opinions
        relevant_stances = self.opinion_service.get_relevant_stances(human, context)
        if relevant_stances:
            # We inject this into the context string (hacky for now, but effective)
            context.recent_thoughts.extend(relevant_stances)

        # 8. Thinking Process
        # Consumes resources
        thought_content, new_intention = self.thinking_service.think(context, human.identity.name)

        # Cost of thinking
        human.state.apply_resource_cost(energy_cost=2.0, attention_cost=5.0)

        # 9. Persist Thought
        human.memory.add_short_term(content=thought_content, importance=0.1)

        # 10. Register Intention (if any)
        if new_intention:
            human.add_intention(new_intention)

        # 11. Inactivity Check
        # If no intention formed, human remains silent (default behavior)