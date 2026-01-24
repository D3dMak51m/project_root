from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
from uuid import UUID, uuid4
from enum import Enum


class ContextLevel(str, Enum):
    L0_GLOBAL = "global"
    L1_COUNTRY = "country"
    L2_REGIONAL = "regional"


@dataclass
class Narrative:
    id: UUID
    title: str
    description: str
    sentiment_score: float  # -1.0 to 1.0
    confidence: float  # 0.0 to 1.0
    keywords: List[str]


@dataclass
class Topic:
    id: UUID
    name: str
    volume: int  # Mention count / popularity
    trending_score: float  # Velocity of growth
    narratives: List[Narrative]


@dataclass
class WorldContextLayer:
    id: UUID
    level: ContextLevel
    scope_id: str  # e.g., "US", "tech_twitter", "global"
    timestamp: datetime
    topics: List[Topic]
    dominant_sentiment: float
    summary: str  # LLM generated summary of the layer

    @classmethod
    def create(cls, level: ContextLevel, scope_id: str) -> 'WorldContextLayer':
        return cls(
            id=uuid4(),
            level=level,
            scope_id=scope_id,
            timestamp=datetime.utcnow(),
            topics=[],
            dominant_sentiment=0.0,
            summary=""
        )