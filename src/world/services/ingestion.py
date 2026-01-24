from typing import List, Dict
from src.world.domain.aggregator import ContextAggregator
from src.world.persistence.repository import WorldContextRepository
from src.world.domain.models import ContextLevel


class WorldIngestionService:
    """
    Service to update the world state.
    In production, this would connect to NewsAPI/TwitterAPI.
    Here, it accepts raw data dictionaries.
    """

    def __init__(self, repo: WorldContextRepository, aggregator: ContextAggregator):
        self.repo = repo
        self.aggregator = aggregator

    def update_context(self, level: ContextLevel, scope_id: str, raw_data: List[Dict]):
        # 1. Aggregate raw data into a structured Layer
        layer = self.aggregator.aggregate(level, scope_id, raw_data)

        # 2. Persist the new state of the world
        self.repo.save(layer)

        # 3. NO NOTIFICATIONS sent to AIHumans.
        # The world updates silently.