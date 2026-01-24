import random
from datetime import datetime
from typing import Optional

from core.domain.persona import PersonaMask
from src.core.domain.entity import AIHuman
from src.core.domain.context import InternalContext
from src.core.services.thinking import ThinkingService
from src.core.services.internalization import InternalizationService
from src.core.services.opinion import OpinionService
from src.core.services.pressure import PressureService
from src.core.services.execution import ExecutionService
from src.core.services.composer import ContentComposer


class LifeLoop:
    """
    The deterministic driver of the AIHuman.
    It orchestrates the sequence:
    Exist -> Perceive(Internal) -> Opinion -> Pressure -> Think -> Form Intention -> Execute(Optional).
    """

    def __init__(
            self,
            thinking_service: ThinkingService,
            internalization_service: InternalizationService,
            opinion_service: OpinionService,
            pressure_service: PressureService,
            execution_service: ExecutionService
    ):
        self.thinking_service = thinking_service
        self.internalization_service = internalization_service
        self.opinion_service = opinion_service
        self.pressure_service = pressure_service
        self.execution_service = execution_service

    def _select_mask(self, human: AIHuman) -> Optional[PersonaMask]:
        """
        Simple strategy: Pick a random mask or based on some internal logic.
        For Stage 8, random valid mask is sufficient.
        """
        if not human.personas:
            return None
        return random.choice(human.personas)

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

        # 5. Form Internal Context (L3) - Initial Build
        # Subjective snapshot of self
        recent_memories = [m.content for m in human.memory.short_term_buffer[-3:]]

        # We build a temporary context to calculate pressure/opinions
        temp_context = InternalContext.build(
            identity=human.identity,
            state=human.state,
            memories=recent_memories,
            intentions_count=len(human.intentions),
            readiness=human.readiness,  # Current readiness
            world_perception=perception  # Passed transiently
        )

        # 6. Opinion Formation
        # Evolve stance based on what was just perceived
        self.opinion_service.form_opinions(human, temp_context)

        # 7. Pressure & Readiness Update
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

        # 8. Re-build Context with Updated Readiness & Stance info
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

        # 9. Thinking Process
        # Consumes resources. Influenced by world, but not controlled by it.
        thought_content, new_intention = self.thinking_service.think(final_context, human.identity.name)

        # Cost of thinking
        human.state.apply_resource_cost(energy_cost=2.0, attention_cost=5.0)

        # 10. Persist Thought
        human.memory.add_short_term(content=thought_content, importance=0.1)

        # 11. Register Intention (if any)
        if new_intention:
            human.add_intention(new_intention)

        # 12. Execution Gate
        if random.random() < 0.1:
            # A. Get Intention
            if not human.intentions:
                return
            intention = human.intentions[0]

            # B. Propose Action (Pure Logic)
            proposal = self.execution_service.propose_action(human, intention)

            if proposal:
                # C. Validate Proposal (Internal State)
                if self.execution_service.validate_proposal(human, proposal):

                    # D. Select Mask (LifeLoop Responsibility)
                    mask = self._select_mask(human)

                    if mask:
                        # E. Validate Mask (Time, Risk, etc.)
                        if self.execution_service.validate_mask(mask, proposal, current_time):

                            # F. Execute
                            result = self.execution_service.execute_action(human, proposal, mask)

                            # G. Apply Results
                            if result.success:
                                human.state.apply_resource_cost(result.energy_cost, attention_cost=10.0)
                                human.readiness.decay(result.readiness_decay)
                                if result.executed_intention_id:
                                    human.intentions = [i for i in human.intentions if i.id != result.executed_intention_id]
                                if result.memory_content:
                                    human.memory.add_short_term(result.memory_content, importance=0.8)
                            elif result.readiness_decay > 0:
                                human.readiness.decay(result.readiness_decay)