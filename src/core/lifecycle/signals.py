from dataclasses import dataclass
from typing import Dict, List, Tuple

@dataclass
class LifeSignals:
    pressure_delta: float
    energy_delta: float
    attention_delta: float
    rest: bool

    perceived_topics: Dict[str, Tuple[float, float]]
    memories: List[str]