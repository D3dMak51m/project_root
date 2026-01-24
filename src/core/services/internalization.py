from typing import Optional
from src.core.domain.entity import AIHuman
from src.world.persistence.repository import WorldContextRepository
from src.world.domain.models import ContextLevel
from src.core.services.filters import PerceptionFilter
from src.core.domain.context import PerceivedWorldSummary
from datetime import datetime


class InternalizationService:
    """
    Bridge between the Objective World and Subjective Mind.
    Pull-based only. Purely functional (no side effects on Human).
    """

    def __init__(self, world_repo: WorldContextRepository, filter_logic: PerceptionFilter):
        self.world_repo = world_repo
        self.filter_logic = filter_logic

    def perceive_world(self, human: AIHuman) -> Optional[PerceivedWorldSummary]:
        """
        Attempts to fetch and internalize world context.
        Returns a transient summary if successful, None otherwise.
        """
        # 1. Check constraints (Blind if sleeping or exhausted)
        if human.state.is_resting or human.state.energy < 15.0:
            return None

        # 2. Pull latest world state
        layer = self.world_repo.get_latest(ContextLevel.L0_GLOBAL, "global")
        if not layer:
            return None

        # 3. Apply Perception Filters
        perceived_topics = self.filter_logic.filter(layer, human.identity, human.state)

        if not perceived_topics:
            return None

        # 4. Subjective Interpretation
        mood = "Neutral"
        if layer.dominant_sentiment < -0.3:
            mood = "Dark"
        elif layer.dominant_sentiment > 0.3:
            mood = "Bright"

        return PerceivedWorldSummary(
            dominant_mood=mood,
            interesting_topics=[t.name for t in perceived_topics],
            uncertainty_level=0.2,
            last_perceived_at=datetime.utcnow().isoformat()
        )