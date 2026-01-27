from dataclasses import dataclass
from src.core.domain.strategic_context import StrategicContext
from src.core.lifecycle.lifeloop import LifeLoop

@dataclass
class StrategicContextRuntime:
    """
    Encapsulates the runtime state of a single strategic context.
    Wraps a LifeLoop instance dedicated to this context.
    """
    context: StrategicContext
    lifeloop: LifeLoop
    tick_count: int = 0
    active: bool = True