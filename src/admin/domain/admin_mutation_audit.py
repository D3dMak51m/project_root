from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict
from uuid import UUID


@dataclass(frozen=True)
class AdminMutationAudit:
    id: UUID
    actor: str
    role: str
    action: str
    target: str
    at: datetime
    before: Dict[str, Any] = field(default_factory=dict)
    after: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
