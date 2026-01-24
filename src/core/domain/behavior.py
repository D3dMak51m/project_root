from dataclasses import dataclass
from datetime import datetime
from src.config.settings import settings


@dataclass
class BehaviorState:
    energy: float = settings.MAX_ENERGY
    attention: float = settings.MAX_ATTENTION
    fatigue: float = 0.0
    last_update: datetime = datetime.utcnow()
    is_resting: bool = False

    def evolve_passive_state(self, current_time: datetime) -> None:
        """
        PASSIVE STATE EVOLUTION.
        Calculates the natural decay or recovery of state parameters over time.
        This is NOT a decision-making process. It is a deterministic calculation.
        """
        delta = current_time - self.last_update
        hours_passed = delta.total_seconds() / 3600.0

        if hours_passed <= 0:
            return

        if self.is_resting:
            # Passive recovery calculation
            recovery = settings.ENERGY_RECOVERY_RATE * hours_passed
            self.energy = min(settings.MAX_ENERGY, self.energy + recovery)

            fatigue_reduction = (settings.ENERGY_RECOVERY_RATE * 0.5) * hours_passed
            self.fatigue = max(0.0, self.fatigue - fatigue_reduction)

            self.attention = min(settings.MAX_ATTENTION, self.attention + (recovery * 0.2))
        else:
            # Passive decay calculation (entropy)
            decay = (settings.ATTENTION_DECAY_RATE * 0.1) * hours_passed
            self.energy = max(0.0, self.energy - decay)
            self.attention = max(0.0, self.attention - decay)

        self.last_update = current_time

    def apply_resource_cost(self, energy_cost: float, attention_cost: float) -> None:
        """
        Direct state modification. Does not imply decision making.
        Used when an external process forces resource consumption.
        """
        self.energy = max(0.0, self.energy - energy_cost)
        self.attention = max(0.0, self.attention - attention_cost)
        self.fatigue = min(settings.MAX_FATIGUE, self.fatigue + (energy_cost * 0.1))

    def set_resting_state(self, is_resting: bool):
        self.is_resting = is_resting