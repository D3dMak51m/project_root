from dataclasses import dataclass
from src.memory.domain.meta_learning_policy import MetaLearningPolicy

@dataclass(frozen=True)
class MetaLearningContext:
    """
    Runtime snapshot of meta-learning conditions.
    Derived from policy, governance state, and system stability.
    """
    policy: MetaLearningPolicy
    is_governance_locked: bool
    is_system_stable: bool
    ticks_since_last_failure: int