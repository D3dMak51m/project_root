from dataclasses import dataclass


@dataclass(frozen=True)
class MetaLearningPolicy:
    """
    Declarative rules governing the strategic learning process.
    Controls when and how much the system can learn from experience.
    """
    learning_enabled: bool = True
    max_learning_delta_per_tick: float = 0.1
    cooldown_ticks_after_failure: int = 10
    require_stability_for_learning: bool = True

    # Default safe policy
    @classmethod
    def default(cls) -> 'MetaLearningPolicy':
        return cls()