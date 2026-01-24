from dataclasses import dataclass, field
from typing import List, Dict
from uuid import UUID

@dataclass
class MemorySystem:
    short_term_buffer: List[str]
    # Placeholder for future vector references
    vector_refs: List[UUID] = field(default_factory=list)