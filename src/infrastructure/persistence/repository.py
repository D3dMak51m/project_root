from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional
from datetime import datetime

from src.core.domain.entity import AIHuman, Stance, Goal
from src.core.domain.identity import Identity, PersonalityTraits
from src.core.domain.behavior import BehaviorState
from src.core.domain.memory import MemorySystem
from src.core.domain.intention import Intention
from src.core.domain.stance import TopicStance
from src.infrastructure.persistence.models import AIHumanModel, IdentityModel, BehaviorStateModel


class AIHumanRepository:
    def __init__(self, session: Session):
        self.session = session

    def _map_to_domain(self, model: AIHumanModel) -> AIHuman:
        # Map Identity
        traits = PersonalityTraits(**model.identity.traits)
        identity = Identity(
            name=model.identity.name,
            age=model.identity.age,
            gender=model.identity.gender,
            biography=model.identity.biography,
            languages=model.identity.languages,
            interests=model.identity.interests,
            traits=traits,
            voice_style=model.identity.voice_style
        )

        # Map State
        state = BehaviorState(
            energy=model.state.energy,
            attention=model.state.attention,
            fatigue=model.state.fatigue,
            last_update=model.state.last_update,
            is_resting=model.state.is_resting
        )

        # Map Memory (Simplified for Stage 1-5 JSON storage)
        memory = MemorySystem()
        # Logic to rehydrate memory from model.memory_data would go here in future

        # Map Stance
        stance = Stance()
        if model.stance_data:
            for topic, data in model.stance_data.items():
                stance.topics[topic] = TopicStance(
                    topic=topic,
                    polarity=data["polarity"],
                    intensity=data["intensity"],
                    confidence=data["confidence"],
                    last_updated=datetime.fromisoformat(data["last_updated"])
                )

        # Map Goals
        goals = [Goal(**g) for g in model.goals_data]

        # Map Intentions
        intentions = []
        for i_data in model.intentions_data:
            intentions.append(Intention(
                id=UUID(i_data['id']),
                type=i_data['type'],
                content=i_data['content'],
                priority=i_data['priority'],
                created_at=datetime.fromisoformat(i_data['created_at']),
                ttl_seconds=i_data['ttl_seconds'],
                metadata=i_data['metadata']
            ))

        return AIHuman(
            id=model.id,
            identity=identity,
            state=state,
            memory=memory,
            stance=stance,
            goals=goals,
            intentions=intentions,
            created_at=model.created_at
        )

    def _map_to_model(self, domain: AIHuman) -> AIHumanModel:
        # Check if exists
        model = self.session.query(AIHumanModel).filter_by(id=domain.id).first()
        if not model:
            model = AIHumanModel(id=domain.id, created_at=domain.created_at)
            model.identity = IdentityModel()
            model.state = BehaviorStateModel()
            self.session.add(model)

        # Update Identity
        model.identity.name = domain.identity.name
        model.identity.age = domain.identity.age
        model.identity.gender = domain.identity.gender
        model.identity.biography = domain.identity.biography
        model.identity.voice_style = domain.identity.voice_style
        model.identity.languages = domain.identity.languages
        model.identity.interests = domain.identity.interests
        model.identity.traits = {
            "openness": domain.identity.traits.openness,
            "conscientiousness": domain.identity.traits.conscientiousness,
            "extraversion": domain.identity.traits.extraversion,
            "agreeableness": domain.identity.traits.agreeableness,
            "neuroticism": domain.identity.traits.neuroticism
        }

        # Update State
        model.state.energy = domain.state.energy
        model.state.attention = domain.state.attention
        model.state.fatigue = domain.state.fatigue
        model.state.last_update = domain.state.last_update
        model.state.is_resting = domain.state.is_resting

        # Update Stance (Serialize)
        stance_dict = {}
        for topic, s in domain.stance.topics.items():
            stance_dict[topic] = {
                "polarity": s.polarity,
                "intensity": s.intensity,
                "confidence": s.confidence,
                "last_updated": s.last_updated.isoformat()
            }
        model.stance_data = stance_dict

        # Update Goals
        model.goals_data = [{"description": g.description, "priority": g.priority} for g in domain.goals]

        # Update Intentions
        model.intentions_data = [
            {
                "id": str(i.id),
                "type": i.type,
                "content": i.content,
                "priority": i.priority,
                "created_at": i.created_at.isoformat(),
                "ttl_seconds": i.ttl_seconds,
                "metadata": i.metadata
            }
            for i in domain.intentions
        ]

        return model

    def save(self, human: AIHuman) -> None:
        self._map_to_model(human)
        self.session.commit()

    def get(self, human_id: UUID) -> Optional[AIHuman]:
        model = self.session.query(AIHumanModel).filter_by(id=human_id).first()
        if not model:
            return None
        return self._map_to_domain(model)