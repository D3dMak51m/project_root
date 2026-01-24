from dataclasses import dataclass
from enum import Enum


class ReadinessLevel(str, Enum):
    PASSIVE = "passive"  # Default state, observing
    RESTLESS = "restless"  # Feeling pressure, thinking more actively
    READY = "ready"  # High pressure, likely to form strong intentions


@dataclass
class ActionReadiness:
    value: float = 0.0  # 0.0 to 100.0
    threshold_restless: float = 40.0
    threshold_ready: float = 80.0

    @property
    def level(self) -> ReadinessLevel:
        if self.value >= self.threshold_ready:
            return ReadinessLevel.READY
        elif self.value >= self.threshold_restless:
            return ReadinessLevel.RESTLESS
        return ReadinessLevel.PASSIVE

    def accumulate(self, amount: float):
        self.value = min(100.0, self.value + amount)

    def decay(self, amount: float):
        self.value = max(0.0, self.value - amount)