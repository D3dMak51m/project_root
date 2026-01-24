from src.core.domain.entity import AIHuman
from src.core.domain.context import InternalContext


class PressureService:
    """
    Calculates internal pressure delta based on Stance, Context, and Intentions.
    Pure logic, no side effects.
    """

    def calculate_delta(self, human: AIHuman, context: InternalContext) -> float:
        pressure_delta = 0.0

        # 1. Stance Pressure
        if context.world_perception:
            for topic in context.world_perception.interesting_topics:
                stance = human.stance.get_stance(topic)
                if stance and stance.intensity > 0.6:
                    pressure_delta += 2.0 * stance.intensity

        # 2. Unresolved Intentions Pressure
        if len(human.intentions) > 0:
            pressure_delta += 1.0 * len(human.intentions)

        # 3. Emotional Tension
        if context.current_mood == "Dark":
            pressure_delta += 1.5

        # 4. Return Delta
        # If positive pressure exists, return it.
        # If no pressure factors, return negative decay rate.
        if pressure_delta > 0:
            return pressure_delta
        else:
            # Natural decay rate
            return -2.0

            # Note: Fatigue dampening logic moved to LifeLoop or handled as a separate modifier
        # to keep this calculation pure regarding "pressure sources".