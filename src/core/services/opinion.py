from typing import List
from src.core.domain.entity import AIHuman
from src.core.domain.context import InternalContext
from src.core.domain.stance import Stance


class OpinionService:
    """
    Analyzes Internal Context and Memory to evolve Stance.
    Does NOT create intentions.
    Does NOT trigger actions.
    """

    def form_opinions(self, human: AIHuman, context: InternalContext) -> None:
        # 1. Check prerequisites
        # If no world perception recently, opinions stagnate
        if not context.world_perception:
            return

        # 2. Analyze Perceived Topics
        # We look at what the human *noticed* (filtered perception)
        for topic_name in context.world_perception.interesting_topics:

            # 3. Calculate Pressure
            # How much does this topic affect the human right now?
            # Based on:
            # - Mood (Dark mood -> negative bias)
            # - Repetition (Memory check would go here in full impl)

            pressure = 0.3  # Base pressure
            sentiment_bias = 0.0

            if context.world_perception.dominant_mood == "Dark":
                sentiment_bias = -0.2
                pressure += 0.1
            elif context.world_perception.dominant_mood == "Bright":
                sentiment_bias = 0.2

            # 4. Evolve Stance
            # This is a silent update of internal state
            human.stance.update_or_create(
                topic=topic_name,
                pressure=pressure,
                sentiment=sentiment_bias
            )

    def get_relevant_stances(self, human: AIHuman, context: InternalContext) -> List[str]:
        """
        Returns a string summary of stances relevant to current context.
        Used to enrich L3 for Thinking.
        """
        if not context.world_perception:
            return []

        relevant = []
        for topic in context.world_perception.interesting_topics:
            s = human.stance.get_stance(topic)
            if s and s.intensity > 0.3:
                sentiment_str = "positive" if s.polarity > 0 else "negative"
                relevant.append(f"I feel {sentiment_str} ({s.intensity:.1f}) about {topic}.")

        return relevant