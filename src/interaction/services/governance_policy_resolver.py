from typing import List
from src.interaction.interfaces.governance_policy_resolver import GovernancePolicyResolver
from src.interaction.domain.policy_decision import PolicyDecision
from src.admin.domain.governance_decision import GovernanceDecision
from src.admin.domain.governance_action import GovernanceAction
from src.admin.domain.governance_scope import GovernanceScope


class StandardGovernancePolicyResolver(GovernancePolicyResolver):
    """
    Deterministic resolver for policy governance.
    Enforces strict priority: REJECT > IMPOSE_CONSTRAINT.
    """

    def apply(
            self,
            decision: PolicyDecision,
            governance: List[GovernanceDecision]
    ) -> PolicyDecision:

        # 1. Deterministic Sorting
        sorted_decisions = sorted(governance, key=lambda d: (d.issued_at, d.id))

        relevant_decisions = [
            d for d in sorted_decisions
            if d.scope in (GovernanceScope.GLOBAL, GovernanceScope.POLICY)
        ]

        new_constraints = list(decision.constraints)
        reasons = [decision.reason] if decision.reason else []

        # 2. Apply Logic
        # Check for REJECT first (Hard Stop)
        for d in relevant_decisions:
            if d.action == GovernanceAction.REJECT:
                return PolicyDecision(
                    allowed=False,
                    reason=f"Governance rejection: {d.justification}",
                    constraints=new_constraints
                )

        # If no reject, apply constraints
        for d in relevant_decisions:
            if d.action == GovernanceAction.IMPOSE_CONSTRAINT:
                constraint = d.effect.get("constraint")
                if constraint:
                    new_constraints.append(constraint)
                    reasons.append(f"Governance constraint: {constraint}")

        return PolicyDecision(
            allowed=decision.allowed,
            reason=" | ".join(reasons),
            constraints=new_constraints
        )