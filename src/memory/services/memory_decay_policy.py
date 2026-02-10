import math
from datetime import timedelta
from src.memory.interfaces.memory_decay_strategy import MemoryDecayStrategy

class LinearDecay(MemoryDecayStrategy):
    def __init__(self, max_age_seconds: float):
        self.max_age_seconds = max_age_seconds

    def decay(self, age: timedelta) -> float:
        age_seconds = age.total_seconds()
        if age_seconds >= self.max_age_seconds:
            return 0.0
        return 1.0 - (age_seconds / self.max_age_seconds)

class ExponentialDecay(MemoryDecayStrategy):
    def __init__(self, half_life_seconds: float):
        self.half_life_seconds = half_life_seconds

    def decay(self, age: timedelta) -> float:
        age_seconds = age.total_seconds()
        if age_seconds < 0:
            return 1.0
        # Formula: N(t) = N0 * (1/2)^(t / half_life)
        return math.pow(0.5, age_seconds / self.half_life_seconds)