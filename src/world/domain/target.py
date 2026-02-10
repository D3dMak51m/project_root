from dataclasses import dataclass, field
from typing import List, Optional
from uuid import UUID
from src.world.domain.geo import Region, Country

@dataclass(frozen=True)
class TargetEntity:
    """
    An entity that can be the target of a signal.
    """
    id: str
    type: str        # "state", "organization", "group", "individual"
    label: str

@dataclass(frozen=True)
class TargetBinding:
    """
    Association of a signal to geographical and entity targets.
    """
    signal_id: UUID
    region: Optional[Region] = None
    country: Optional[Country] = None
    targets: List[TargetEntity] = field(default_factory=list)