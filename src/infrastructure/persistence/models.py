from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_base, relationship
import uuid
from datetime import datetime

Base = declarative_base()


class AIHumanModel(Base):
    __tablename__ = "ai_humans"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    identity = relationship("IdentityModel", back_populates="human", uselist=False, cascade="all, delete-orphan")
    state = relationship("BehaviorStateModel", back_populates="human", uselist=False, cascade="all, delete-orphan")
    # Stance and Goals stored as JSON for flexibility in Stage 1
    stance_data = Column(JSON, default={})
    goals_data = Column(JSON, default=[])
    # Memory is complex, storing basic structure as JSON for Stage 1,
    # will evolve to vector references later
    memory_data = Column(JSON, default={})


class IdentityModel(Base):
    __tablename__ = "identities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    human_id = Column(PG_UUID(as_uuid=True), ForeignKey("ai_humans.id"), unique=True)

    name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String, nullable=False)
    biography = Column(String, nullable=False)
    voice_style = Column(String, nullable=True)

    # Storing lists/dicts as JSONB
    languages = Column(JSON, default=[])
    interests = Column(JSON, default=[])
    traits = Column(JSON, default={})  # Openness, etc.

    human = relationship("AIHumanModel", back_populates="identity")


class BehaviorStateModel(Base):
    __tablename__ = "behavior_states"

    id = Column(Integer, primary_key=True, autoincrement=True)
    human_id = Column(PG_UUID(as_uuid=True), ForeignKey("ai_humans.id"), unique=True)

    energy = Column(Float, default=100.0)
    attention = Column(Float, default=100.0)
    fatigue = Column(Float, default=0.0)
    last_update = Column(DateTime, default=datetime.utcnow)
    is_resting = Column(Boolean, default=False)

    human = relationship("AIHumanModel", back_populates="state")