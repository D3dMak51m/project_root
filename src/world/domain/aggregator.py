from typing import List, Dict
from src.world.domain.models import WorldContextLayer, Topic, Narrative, ContextLevel
from uuid import uuid4


class ContextAggregator:
    """
    Pure logic to transform raw signals into structured Context Layers.
    Does NOT fetch data. Only processes input.
    """

    def aggregate(self, level: ContextLevel, scope_id: str, raw_signals: List[Dict]) -> WorldContextLayer:
        # 1. Create empty layer
        layer = WorldContextLayer.create(level, scope_id)

        # 2. Mock Aggregation Logic (In real system: Clustering + LLM Summarization)
        # For Stage 3, we simulate the extraction of topics from raw signals

        topics_map = {}

        for signal in raw_signals:
            topic_name = signal.get("topic", "General")
            if topic_name not in topics_map:
                topics_map[topic_name] = {
                    "volume": 0,
                    "sentiment_sum": 0.0,
                    "narratives": []
                }

            t_data = topics_map[topic_name]
            t_data["volume"] += 1
            t_data["sentiment_sum"] += signal.get("sentiment", 0.0)

            # Simple narrative extraction mock
            if "narrative" in signal:
                t_data["narratives"].append(
                    Narrative(
                        id=uuid4(),
                        title=signal["narrative"],
                        description=signal.get("content", "")[:50],
                        sentiment_score=signal.get("sentiment", 0.0),
                        confidence=0.8,
                        keywords=signal.get("keywords", [])
                    )
                )

        # 3. Build Topic Objects
        for name, data in topics_map.items():
            avg_sentiment = data["sentiment_sum"] / max(1, data["volume"])

            topic = Topic(
                id=uuid4(),
                name=name,
                volume=data["volume"],
                trending_score=float(data["volume"]) * 0.1,  # Mock calculation
                narratives=data["narratives"]
            )
            layer.topics.append(topic)

        # 4. Calculate Layer Metadata
        if layer.topics:
            total_sentiment = sum(t.narratives[0].sentiment_score for t in layer.topics if t.narratives)
            layer.dominant_sentiment = total_sentiment / max(1, len(layer.topics))
            layer.summary = f"Context {level.value} ({scope_id}) contains {len(layer.topics)} topics."

        return layer