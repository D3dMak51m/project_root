from dataclasses import dataclass
from typing import Dict
from datetime import datetime

@dataclass
class ReputationProfile:
    scope: str  # person | group | platform
    expectation_map: Dict[str, float]
    emotional_residue: Dict[str, float]
    last_updated: datetime