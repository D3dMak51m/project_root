from dataclasses import dataclass
from typing import Dict
from datetime import datetime

@dataclass
class TopicStance:
    topic: str
    polarity: float
    intensity: float
    confidence: float
    last_updated: datetime

@dataclass
class Stance:
    topics: Dict[str, TopicStance]