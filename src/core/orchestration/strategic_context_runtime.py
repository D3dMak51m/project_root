from dataclasses import dataclass
from src.core.domain.strategic_context import StrategicContext
from src.core.lifecycle.lifeloop import LifeLoop


@dataclass
class StrategicContextRuntime:
    """
    Encapsulates the runtime state of a single strategic context.
    Wraps a LifeLoop instance dedicated to this context.
    Tracks orchestration-level metrics like starvation.
    """
    context: StrategicContext
    lifeloop: LifeLoop
    tick_count: int = 0
    active: bool = True

    # [NEW] Starvation tracking
    starvation_score: float = 0.0
    last_win_tick: int = 0