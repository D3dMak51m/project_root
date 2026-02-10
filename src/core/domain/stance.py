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

    def apply_pressure(self, pressure: float, sentiment: float, now: datetime) -> None:
        inertia = 0.1 + self.confidence * 0.8
        rate = (1.0 - inertia) * 0.2

        self.intensity = min(1.0, max(0.0, self.intensity + (pressure - self.intensity) * rate))
        self.polarity = max(-1.0, min(1.0, self.polarity + (sentiment - self.polarity) * rate))
        self.confidence = min(1.0, self.confidence + 0.05 if abs(sentiment - self.polarity) < 0.4 else self.confidence - 0.05)
        self.last_updated = now


@dataclass
class Stance:
    topics: Dict[str, TopicStance]

    def update_topic(self, topic: str, pressure: float, sentiment: float, now: datetime) -> None:
        if topic not in self.topics:
            self.topics[topic] = TopicStance(
                topic=topic,
                polarity=sentiment,
                intensity=pressure * 0.5,
                confidence=0.1,
                last_updated=now
            )
        else:
            self.topics[topic].apply_pressure(pressure, sentiment, now)