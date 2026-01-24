from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime


@dataclass
class TopicStance:
    topic: str
    polarity: float  # -1.0 (Negative) to 1.0 (Positive)
    intensity: float  # 0.0 (Indifferent) to 1.0 (Fanatic)
    confidence: float  # 0.0 (Unsure) to 1.0 (Certain)
    last_updated: datetime

    def adjust(self, pressure: float, sentiment: float):
        """
        Evolve stance based on new pressure.
        Stance is resistant to change (inertia).
        """
        # 1. Intensity update (slowly moves towards pressure)
        # Resistance factor: higher confidence = harder to change
        resistance = 0.1 + (self.confidence * 0.8)
        change_rate = (1.0 - resistance) * 0.2

        self.intensity += (pressure - self.intensity) * change_rate

        # 2. Polarity update (weighted by intensity)
        # If intensity is high, polarity is harder to flip
        polarity_delta = (sentiment - self.polarity) * change_rate
        self.polarity = max(-1.0, min(1.0, self.polarity + polarity_delta))

        # 3. Confidence grows with reinforcement, decays with conflict
        if abs(sentiment - self.polarity) < 0.5:
            self.confidence = min(1.0, self.confidence + 0.05)
        else:
            self.confidence = max(0.0, self.confidence - 0.1)

        self.last_updated = datetime.utcnow()


@dataclass
class Stance:
    # Map topic_name -> TopicStance
    topics: Dict[str, TopicStance] = field(default_factory=dict)

    def get_stance(self, topic: str) -> Optional[TopicStance]:
        return self.topics.get(topic)

    def update_or_create(self, topic: str, pressure: float, sentiment: float):
        if topic not in self.topics:
            self.topics[topic] = TopicStance(
                topic=topic,
                polarity=sentiment,
                intensity=pressure * 0.5,  # Start weak
                confidence=0.1,
                last_updated=datetime.utcnow()
            )
        else:
            self.topics[topic].adjust(pressure, sentiment)