from dataclasses import dataclass, field
from typing import List, Optional, Set
from src.admin.domain.governance_decision import GovernanceDecision
from src.admin.domain.governance_scope import GovernanceScope
from src.admin.domain.governance_action import GovernanceAction
from src.autonomy.domain.autonomy_mode import AutonomyMode


@dataclass(frozen=True)
class RuntimeGovernanceContext:
    """
    Immutable snapshot of active governance decisions for a single runtime cycle.
    Pre-resolves conflicts and exposes effective governance state.
    """
    # Autonomy State
    is_autonomy_locked: bool
    lock_reason: str
    override_mode: Optional[AutonomyMode]
    override_reason: str

    # Policy State
    is_policy_rejected: bool
    policy_rejection_reason: str
    policy_constraints: List[str]

    # Execution State
    is_execution_locked: bool
    execution_lock_reason: str

    @classmethod
    def build(cls, decisions: List[GovernanceDecision]) -> 'RuntimeGovernanceContext':
        # Decisions are assumed to be passed in chronological order of issuance

        # 1. Autonomy Resolution
        is_autonomy_locked = False
        lock_reason = ""
        override_mode = None
        override_reason = ""

        for d in decisions:
            if d.scope in (GovernanceScope.GLOBAL, GovernanceScope.AUTONOMY):
                if d.action == GovernanceAction.LOCK_AUTONOMY:
                    is_autonomy_locked = True
                    lock_reason = d.justification
                elif d.action == GovernanceAction.UNLOCK_AUTONOMY:
                    is_autonomy_locked = False
                    lock_reason = ""
                elif d.action == GovernanceAction.OVERRIDE_MODE:
                    mode_str = d.effect.get("mode")
                    if mode_str:
                        try:
                            override_mode = AutonomyMode(mode_str)
                            override_reason = d.justification
                        except ValueError:
                            pass

        # 2. Policy Resolution
        is_policy_rejected = False
        policy_rejection_reason = ""
        policy_constraints = []

        for d in decisions:
            if d.scope in (GovernanceScope.GLOBAL, GovernanceScope.POLICY):
                if d.action == GovernanceAction.REJECT:
                    is_policy_rejected = True
                    policy_rejection_reason = d.justification
                elif d.action == GovernanceAction.IMPOSE_CONSTRAINT:
                    constraint = d.effect.get("constraint")
                    if constraint:
                        policy_constraints.append(constraint)
                elif d.action == GovernanceAction.LIFT_CONSTRAINT:
                    constraint = d.effect.get("constraint")
                    if constraint and constraint in policy_constraints:
                        policy_constraints.remove(constraint)

        # 3. Execution Resolution
        is_execution_locked = False
        execution_lock_reason = ""

        for d in decisions:
            if d.scope == GovernanceScope.GLOBAL:
                if d.action == GovernanceAction.LOCK_AUTONOMY:
                    is_execution_locked = True
                    execution_lock_reason = d.justification
                elif d.action == GovernanceAction.UNLOCK_AUTONOMY:
                    is_execution_locked = False
                    execution_lock_reason = ""

            if d.scope == GovernanceScope.EXECUTION:
                if d.action == GovernanceAction.IMPOSE_CONSTRAINT:
                    constraint = d.effect.get("constraint")
                    if constraint == "EMERGENCY_STOP":
                        is_execution_locked = True
                        execution_lock_reason = f"Governance constraint: {constraint}"
                elif d.action == GovernanceAction.LIFT_CONSTRAINT:
                    constraint = d.effect.get("constraint")
                    if constraint == "EMERGENCY_STOP":
                        is_execution_locked = False
                        execution_lock_reason = ""

        return cls(
            is_autonomy_locked=is_autonomy_locked,
            lock_reason=lock_reason,
            override_mode=override_mode,
            override_reason=override_reason,
            is_policy_rejected=is_policy_rejected,
            policy_rejection_reason=policy_rejection_reason,
            policy_constraints=policy_constraints,
            is_execution_locked=is_execution_locked,
            execution_lock_reason=execution_lock_reason
        )