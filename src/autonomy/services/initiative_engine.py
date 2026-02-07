from src.autonomy.interfaces.initiative_engine import InitiativeEngine
from src.autonomy.domain.initiative_decision import InitiativeDecision
from src.autonomy.domain.autonomy_mode import AutonomyMode
from src.interaction.domain.envelope import InteractionEnvelope, PriorityHint
from src.interaction.domain.policy_decision import PolicyDecision
from src.autonomy.domain.autonomy_state import AutonomyState
from src.core.config.runtime_profile import RuntimeProfile


class StandardInitiativeEngine(InitiativeEngine):
    """
    Deterministic engine for initiative decisions.
    Evaluates readiness, policy, and priority to decide on action initiation.
    """

    def evaluate(
            self,
            envelope: InteractionEnvelope,
            policy: PolicyDecision,
            autonomy: AutonomyState,
            profile: RuntimeProfile
    ) -> InitiativeDecision:

        # 1. Autonomy Mode Check
        if autonomy.mode != AutonomyMode.READY:
            # If escalation is required, we defer to human
            if autonomy.requires_human:
                return InitiativeDecision.DEFER
            # Otherwise (BLOCKED, SILENT), we hold
            return InitiativeDecision.HOLD

        # 2. Policy Check
        if not policy.allowed:
            return InitiativeDecision.HOLD

        # 3. Human Requirement Check (Redundant but explicit safety)
        if autonomy.requires_human:
            return InitiativeDecision.DEFER

        # 4. Priority & Pressure Logic (for READY state)
        if envelope.priority_hint == PriorityHint.HIGH:
            return InitiativeDecision.INITIATE

        if envelope.priority_hint == PriorityHint.NORMAL:
            # Threshold check: pressure must be sufficient for normal priority
            if autonomy.pressure_level >= 0.5:
                return InitiativeDecision.INITIATE
            return InitiativeDecision.HOLD

        if envelope.priority_hint == PriorityHint.LOW:
            return InitiativeDecision.HOLD

        # Default fallback
        return InitiativeDecision.HOLD