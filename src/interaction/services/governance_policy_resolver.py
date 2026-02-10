from src.interaction.interfaces.governance_policy_resolver import GovernancePolicyResolver
from src.interaction.domain.policy_decision import PolicyDecision
from src.governance.runtime.governance_runtime_context import RuntimeGovernanceContext


class StandardGovernancePolicyResolver(GovernancePolicyResolver):
    """
    Deterministic resolver for policy governance.
    Applies pre-resolved governance state from context.
    """

    def apply(
            self,
            decision: PolicyDecision,
            context: RuntimeGovernanceContext
    ) -> PolicyDecision:

        new_constraints = list(decision.constraints)
        reasons = [decision.reason] if decision.reason else []

        # 1. Check Rejection (Hard Stop)
        if context.is_policy_rejected:
            return PolicyDecision(
                allowed=False,
                reason=f"Governance rejection: {context.policy_rejection_reason}",
                constraints=new_constraints
            )

        # 2. Apply Constraints
        for constraint in context.policy_constraints:
            new_constraints.append(constraint)
            reasons.append(f"Governance constraint: {constraint}")

        return PolicyDecision(
            allowed=decision.allowed,
            reason=" | ".join(reasons),
            constraints=new_constraints
        )