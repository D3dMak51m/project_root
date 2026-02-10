from dataclasses import dataclass
from typing import Optional
from src.governance.runtime.governance_runtime_context import RuntimeGovernanceContext

@dataclass(frozen=True)
class GovernanceSnapshot:
    """
    Lightweight, immutable snapshot of governance state at the time of an event.
    """
    is_autonomy_locked: bool
    is_policy_rejected: bool
    is_execution_locked: bool

    @classmethod
    def from_context(cls, context: RuntimeGovernanceContext) -> 'GovernanceSnapshot':
        return cls(
            is_autonomy_locked=context.is_autonomy_locked,
            is_policy_rejected=context.is_policy_rejected,
            is_execution_locked=context.is_execution_locked
        )

    @classmethod
    def empty(cls) -> 'GovernanceSnapshot':
        return cls(
            is_autonomy_locked=False,
            is_policy_rejected=False,
            is_execution_locked=False
        )