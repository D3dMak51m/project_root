from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime
from uuid import UUID, uuid4

@dataclass
class MemoryItem:
    id: UUID
    content: str
    timestamp: datetime
    importance: float  # 0.0 - 1.0
    tags: List[str]
    # Embeddings will be added here in later stages, currently strictly structural

@dataclass
class PersonProfile:
    id: UUID
    name: str
    relationship_level: float  # -1.0 (enemy) to 1.0 (ally)
    interaction_history_count: int
    last_interaction: datetime
    notes: str

@dataclass
class MemorySystem:
    short_term_buffer: List[MemoryItem] = field(default_factory=list)
    known_people: Dict[UUID, PersonProfile] = field(default_factory=dict)
    recurring_themes: List[str] = field(default_factory=list)

    def add_short_term(self, content: str, importance: float = 0.5):
        item = MemoryItem(
            id=uuid4(),
            content=content,
            timestamp=datetime.utcnow(),
            importance=importance,
            tags=[]
        )
        self.short_term_buffer.append(item)

    def get_person(self, person_id: UUID) -> Optional[PersonProfile]:
        return self.known_people.get(person_id)