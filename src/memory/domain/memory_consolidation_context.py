from dataclasses import dataclass
from datetime import datetime
from src.memory.domain.memory_retention_policy import MemoryRetentionPolicy

@dataclass(frozen=True)
class MemoryConsolidationContext:
    """
    Runtime snapshot of consolidation conditions.
    Passive data container, no logic or interpretation.
    """
    policy: MemoryRetentionPolicy
    current_time: datetime