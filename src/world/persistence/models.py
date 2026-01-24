from sqlalchemy import Column, String, Integer, Float, DateTime, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from src.infrastructure.persistence.models import Base
from src.world.domain.models import ContextLevel
import uuid
from datetime import datetime


class WorldContextModel(Base):
    __tablename__ = "world_contexts"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    level = Column(SQLEnum(ContextLevel), nullable=False)
    scope_id = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    dominant_sentiment = Column(Float, default=0.0)
    summary = Column(String, nullable=True)

    # Storing structured topics/narratives as JSONB for flexibility
    # In a high-load system, this might be normalized tables,
    # but for Context snapshots JSON is often superior for read-heavy workloads.
    topics_data = Column(JSON, default=[])