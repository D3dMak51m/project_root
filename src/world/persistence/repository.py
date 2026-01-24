from sqlalchemy.orm import Session
from typing import Optional, List
from src.world.domain.models import WorldContextLayer, Topic, Narrative, ContextLevel
from src.world.persistence.models import WorldContextModel
from uuid import UUID


class WorldContextRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, layer: WorldContextLayer) -> None:
        # Serialize topics to JSON
        topics_json = []
        for t in layer.topics:
            t_dict = {
                "id": str(t.id),
                "name": t.name,
                "volume": t.volume,
                "trending_score": t.trending_score,
                "narratives": [
                    {
                        "id": str(n.id),
                        "title": n.title,
                        "description": n.description,
                        "sentiment": n.sentiment_score,
                        "confidence": n.confidence,
                        "keywords": n.keywords
                    } for n in t.narratives
                ]
            }
            topics_json.append(t_dict)

        model = WorldContextModel(
            id=layer.id,
            level=layer.level,
            scope_id=layer.scope_id,
            timestamp=layer.timestamp,
            dominant_sentiment=layer.dominant_sentiment,
            summary=layer.summary,
            topics_data=topics_json
        )
        self.session.add(model)
        self.session.commit()

    def get_latest(self, level: ContextLevel, scope_id: str) -> Optional[WorldContextLayer]:
        model = self.session.query(WorldContextModel) \
            .filter_by(level=level, scope_id=scope_id) \
            .order_by(WorldContextModel.timestamp.desc()) \
            .first()

        if not model:
            return None

        # Deserialize (Simplified for brevity)
        topics = []
        for t_data in model.topics_data:
            narratives = [
                Narrative(
                    id=UUID(n["id"]),
                    title=n["title"],
                    description=n["description"],
                    sentiment_score=n["sentiment"],
                    confidence=n["confidence"],
                    keywords=n["keywords"]
                ) for n in t_data["narratives"]
            ]
            topics.append(Topic(
                id=UUID(t_data["id"]),
                name=t_data["name"],
                volume=t_data["volume"],
                trending_score=t_data["trending_score"],
                narratives=narratives
            ))

        return WorldContextLayer(
            id=model.id,
            level=model.level,
            scope_id=model.scope_id,
            timestamp=model.timestamp,
            topics=topics,
            dominant_sentiment=model.dominant_sentiment,
            summary=model.summary
        )