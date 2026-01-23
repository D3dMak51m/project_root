from dataclasses import dataclass
from datetime import datetime, timedelta
from src.config.settings import settings


@dataclass
class BehaviorState:
    energy: float = settings.MAX_ENERGY
    attention: float = settings.MAX_ATTENTION
    fatigue: float = 0.0
    last_update: datetime = datetime.utcnow()
    is_resting: bool = False

    def update_over_time(self, current_time: datetime) -> None:
        """
        Pure logic calculation of state changes over time.
        No side effects, just math based on delta.
        """
        delta = current_time - self.last_update
        hours_passed = delta.total_seconds() / 3600.0

        if hours_passed <= 0:
            return

        if self.is_resting:
            # Recover energy, reduce fatigue
            recovery = settings.ENERGY_RECOVERY_RATE * hours_passed
            self.energy = min(settings.MAX_ENERGY, self.energy + recovery)

            fatigue_reduction = (settings.ENERGY_RECOVERY_RATE * 0.5) * hours_passed
            self.fatigue = max(0.0, self.fatigue - fatigue_reduction)

            # Attention recovers slightly during rest
            self.attention = min(settings.MAX_ATTENTION, self.attention + (recovery * 0.2))
        else:
            # Passive decay while awake but idle
            decay = (settings.ATTENTION_DECAY_RATE * 0.1) * hours_passed
            self.energy = max(0.0, self.energy - decay)
            self.attention = max(0.0, self.attention - decay)

        self.last_update = current_time

    def consume_resources(self, energy_cost: float, attention_cost: float) -> bool:
        """
        Attempt to perform an action. Returns False if exhausted.
        """
        if self.energy < energy_cost or self.attention < attention_cost:
            return False

        self.energy -= energy_cost
        self.attention -= attention_cost
        self.fatigue = min(settings.MAX_FATIGUE, self.fatigue + (energy_cost * 0.1))
        return True

    def start_rest(self):
        self.is_resting = True

    def stop_rest(self):
        self.is_resting = False