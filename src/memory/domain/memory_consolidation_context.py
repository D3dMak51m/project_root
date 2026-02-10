from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from src.memory.domain.memory_retention_policy import MemoryRetentionPolicy

class ConsolidationMode(Enum):
    OFF = "OFF"
    CONSERVATIVE = "CONSERVATIVE" # Only drop very old/irrelevant
    AGGRESSIVE = "AGGRESSIVE"     # Drop everything non-essential

@dataclass(frozen=True)
class MemoryConsolidationContext:
    """
    Runtime snapshot of consolidation conditions.
    """
    policy: MemoryRetentionPolicy
    mode: ConsolidationMode
    current_time: datetime
    is_governance_locked: bool