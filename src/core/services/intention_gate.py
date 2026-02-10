import random
from src.core.domain.behavior import BehaviorState
from src.core.domain.intention_candidate import IntentionCandidate


class IntentionGate:
    """
    Pure service. The 'Great Filter' for impulses.
    Decides if a candidate becomes an Intention.
    """

    def allow(self, candidate: IntentionCandidate, state: BehaviorState) -> bool:
        # 1. Energy Check
        # Forming an intention costs energy. If low, reject.
        if state.energy < 20.0:
            return False

        # 2. Fatigue Check
        # If tired, resistance is high.
        if state.fatigue > 80.0:
            return False

        # 3. Pressure Threshold
        # Weak impulses die.
        if candidate.pressure < 50.0:
            return False

        # 4. Probabilistic Resistance
        # Even perfect conditions don't guarantee formation.
        # Higher pressure = higher chance, but never 100%.
        acceptance_chance = (candidate.pressure / 200.0)  # Max 50% chance at 100 pressure

        return random.random() < acceptance_chance