from typing import List
from src.world.domain.models import WorldContextLayer, Topic
from src.core.domain.identity import Identity
from src.core.domain.behavior import BehaviorState


class PerceptionFilter:
    """
    Determines WHAT the AIHuman notices in the world.
    Based on interests, state, and randomness.
    """

    def filter(self, layer: WorldContextLayer, identity: Identity, state: BehaviorState) -> List[Topic]:
        # 1. Fatigue Check: If tired, perceive almost nothing
        if state.fatigue > 80.0:
            return []

        # 2. Attention Budget: Higher attention = more topics perceived
        max_topics = int(state.attention / 20.0) + 1  # 1 to 6 topics

        perceived_topics = []

        for topic in layer.topics:
            if len(perceived_topics) >= max_topics:
                break

            score = 0.0

            # Interest Match
            for interest in identity.interests:
                if interest.lower() in topic.name.lower():
                    score += 2.0

            # Volume/Hype factor (harder to ignore loud things)
            if topic.volume > 1000:
                score += 0.5

            # Random noise factor (simulating imperfect perception)
            # In production, use random.random()
            # Here deterministic for Stage 4 requirements
            score += 0.1

            # Threshold for perception
            if score > 1.0:
                perceived_topics.append(topic)

        return perceived_topics