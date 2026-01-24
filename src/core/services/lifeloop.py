from datetime import datetime
from src.core.domain.entity import AIHuman
from src.core.domain.context import InternalContext
from src.core.services.thinking import ThinkingService


class LifeLoop:
    """
    The deterministic driver of the AIHuman.
    It orchestrates the sequence: Exist -> Perceive(Internal) -> Think -> Form Intention.
    """

    def __init__(self, thinking_service: ThinkingService):
        self.thinking_service = thinking_service

    def tick(self, human: AIHuman, current_time: datetime) -> None:
        # 1. Passive Existence (Physics of the mind)
        # Updates energy, fatigue, cleans up dead intentions
        human.exist(current_time)

        # 2. Check constraints (Fatigue check)
        # If too tired, force rest or skip thinking
        if human.state.energy < 10.0:
            human.state.set_resting_state(True)
            return

        # 3. Form Internal Context (L3)
        # Subjective snapshot of self
        # In Stage 2, we fetch last 3 memories as "recent thoughts"
        recent_memories = [m.content for m in human.memory.short_term_buffer[-3:]]
        context = InternalContext.build(
            identity=human.identity,
            state=human.state,
            memories=recent_memories,
            intentions_count=len(human.intentions)
        )

        # 4. Thinking Process
        # Consumes resources
        thought_content, new_intention = self.thinking_service.think(context, human.identity.name)

        # Cost of thinking
        human.state.apply_resource_cost(energy_cost=2.0, attention_cost=5.0)

        # 5. Persist Thought
        human.memory.add_short_term(content=thought_content, importance=0.1)

        # 6. Register Intention (if any)
        if new_intention:
            human.add_intention(new_intention)

        # 7. Inactivity Check
        # If no intention formed, human remains silent (default behavior)