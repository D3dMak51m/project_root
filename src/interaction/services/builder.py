from typing import List
from uuid import uuid4
from src.interaction.interfaces.builder import InteractionBuilder
from src.interaction.domain.context import InteractionContext
from src.interaction.domain.intent import InteractionIntent, InteractionType

class StandardInteractionBuilder(InteractionBuilder):
    """
    Deterministic builder that translates cognitive artifacts into interaction intents.
    Does NOT decide to send. Does NOT prioritize.
    """
    def build(self, context: InteractionContext) -> List[InteractionIntent]:
        intents = []

        # 1. Narrative Report Intent
        # Always generate a report intent based on the narrative
        intents.append(InteractionIntent(
            id=uuid4(),
            type=InteractionType.REPORT,
            content=context.narrative.summary,
            metadata={"source": "narrative_generator"}
        ))

        # 2. Uncertainty Questions
        # If there are significant uncertainties, form a question intent
        if context.reasoning.uncertainties:
            question_content = f"Clarification needed on: {', '.join(context.reasoning.uncertainties[:3])}"
            intents.append(InteractionIntent(
                id=uuid4(),
                type=InteractionType.QUESTION,
                content=question_content,
                metadata={"source": "reasoning_engine", "uncertainty_count": len(context.reasoning.uncertainties)}
            ))

        # 3. Observation Notifications
        # If there are high-salience observations, form a notification intent
        for obs in context.observations:
            if obs.salience.salience_score > 0.8:
                intents.append(InteractionIntent(
                    id=uuid4(),
                    type=InteractionType.NOTIFICATION,
                    content=f"High salience signal detected from {obs.signal.source_id}",
                    metadata={
                        "signal_id": str(obs.signal.signal_id),
                        "salience": obs.salience.salience_score
                    }
                ))

        return intents