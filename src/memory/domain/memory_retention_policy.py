from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryRetentionPolicy:
    """
    Declarative rules for memory retention and forgetting.
    Controls how long events are kept and which ones are prioritized.
    """
    max_events_per_context: int = 1000
    retain_successful_events: bool = True
    retain_last_n_failures: int = 50
    retain_counterfactuals: bool = True
    max_counterfactuals_per_context: int = 500
    long_term_window_days: int = 30

    @classmethod
    def default(cls) -> 'MemoryRetentionPolicy':
        return cls()