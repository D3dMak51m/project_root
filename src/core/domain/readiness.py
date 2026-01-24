from dataclasses import dataclass

@dataclass
class ActionReadiness:
    value: float
    threshold_restless: float
    threshold_ready: float

    def accumulate(self, delta: float) -> None:
        self.value = min(100.0, self.value + max(0.0, delta))

    def decay(self, delta: float) -> None:
        self.value = max(0.0, self.value - max(0.0, delta))

    def level(self) -> str:
        if self.value >= self.threshold_ready:
            return "ready"
        if self.value >= self.threshold_restless:
            return "restless"
        return "passive"