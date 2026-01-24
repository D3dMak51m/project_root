from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from src.core.domain.execution_result import ExecutionResult


@dataclass
class LifeSignals:
    pressure_delta: float
    energy_delta: float
    attention_delta: float
    rest: bool

    perceived_topics: Dict[str, Tuple[float, float]]
    memories: List[str]

    # [NEW] Feedback from execution (if any)
    # This allows LifeLoop to process the outcome of the previous tick's action
    execution_feedback: Optional[ExecutionResult] = None