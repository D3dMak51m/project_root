from dataclasses import dataclass
from datetime import datetime

@dataclass
class BehaviorState:
    energy: float
    attention: float
    fatigue: float
    last_update: datetime
    is_resting: bool