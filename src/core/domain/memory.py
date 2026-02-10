from dataclasses import dataclass, field
from typing import List
from uuid import UUID

@dataclass
class MemorySystem:
    short_term_buffer: List[str]
    vector_refs: List[UUID] = field(default_factory=list)

    def add_short(self, content: str, limit: int = 10) -> None:
        self.short_term_buffer.append(content)
        if len(self.short_term_buffer) > limit:
            self.short_term_buffer.pop(0)

    def recent(self, n: int) -> List[str]:
        return self.short_term_buffer[-n:]