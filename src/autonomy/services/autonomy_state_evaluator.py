from src.autonomy.interfaces.state_evaluator import AutonomyStateEvaluator
from src.autonomy.domain.autonomy_state import AutonomyState
from src.autonomy.domain.autonomy_mode import AutonomyMode
from src.interaction.domain.envelope import InteractionEnvelope, PriorityHint
from src.interaction.domain.policy_decision import PolicyDecision
from src.core.config.runtime_profile import RuntimeProfile


class StandardAutonomyStateEvaluator(AutonomyStateEvaluator):
    """
    Deterministic evaluator of autonomy state based on policy and envelope.
    """

    def evaluate(
            self,
            envelope: InteractionEnvelope,
            policy: PolicyDecision,
            profile: RuntimeProfile
    ) -> AutonomyState:

        # 1. Policy Blocked
        if not policy.allowed:
            return AutonomyState(
                mode=AutonomyMode.BLOCKED,
                justification=f"Policy denied: {policy.reason}",
                pressure_level=0.0,
                constraints=policy.constraints,
                requires_human=False
            )

        # 2. Escalation Required (Constraints Check)
        escalation_triggers = {"requires_approval", "audit_logging"}
        # Check if any policy constraint matches triggers
        needs_escalation = any(c in escalation_triggers for c in policy.constraints)

        if needs_escalation:
            return AutonomyState(
                mode=AutonomyMode.ESCALATION_REQUIRED,
                justification="Policy constraints require human oversight",
                pressure_level=0.7,
                constraints=policy.constraints,
                requires_human=True
            )

        # 3. Low Priority Downgrade
        if envelope.priority_hint == PriorityHint.LOW:
            return AutonomyState(
                mode=AutonomyMode.SILENT,
                justification="Low priority interaction defaults to silence",
                pressure_level=0.1,
                constraints=policy.constraints,
                requires_human=False
            )

        # 4. Ready State
        return AutonomyState(
            mode=AutonomyMode.READY,
            justification="Policy allowed, priority sufficient",
            pressure_level=0.5,
            constraints=policy.constraints,
            requires_human=False
        )