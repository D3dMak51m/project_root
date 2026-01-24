from dataclasses import dataclass
from datetime import datetime

@dataclass
class BehaviorState:
    energy: float
    attention: float
    fatigue: float
    last_update: datetime
    is_resting: bool

    def apply_cost(self, energy_cost: float, attention_cost: float) -> None:
        self.energy = max(0.0, self.energy - energy_cost)
        self.attention = max(0.0, self.attention - attention_cost)
        self.fatigue = min(100.0, self.fatigue + (energy_cost * 0.5))

    def recover(self, energy_gain: float, attention_gain: float) -> None:
        self.energy = min(100.0, self.energy + energy_gain)
        self.attention = min(100.0, self.attention + attention_gain)
        self.fatigue = max(0.0, self.fatigue - (energy_gain * 0.3))

    def set_resting(self, resting: bool) -> None:
        self.is_resting = resting