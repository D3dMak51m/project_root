from typing import List
from src.interaction.interfaces.policy import InteractionPolicy
from src.interaction.domain.envelope import InteractionEnvelope, Visibility, TargetHint
from src.interaction.domain.policy_decision import PolicyDecision
from src.core.config.runtime_profile import RuntimeProfile, Environment


class StandardInteractionPolicy(InteractionPolicy):
    """
    Deterministic policy engine enforcing safety, environment rules, and visibility constraints.
    """

    def evaluate(
            self,
            envelope: InteractionEnvelope,
            profile: RuntimeProfile
    ) -> PolicyDecision:

        # 1. Global Execution Guard
        # If execution is globally disabled in profile, block external interactions
        if not profile.allow_execution:
            if envelope.visibility == Visibility.EXTERNAL:
                return PolicyDecision(
                    allowed=False,
                    reason="Execution disabled in current runtime profile",
                    constraints=["profile_lock"]
                )

        # 2. Environment-Specific Rules
        if profile.env == Environment.REPLAY:
            # Replay mode strictly forbids external interaction
            if envelope.visibility == Visibility.EXTERNAL:
                return PolicyDecision(
                    allowed=False,
                    reason="External interaction forbidden in REPLAY mode",
                    constraints=["replay_isolation"]
                )

        elif profile.env == Environment.TEST:
            # Test mode allows internal/mocked interactions, but might gate external
            # Assuming test harness handles mocking, we allow if execution is enabled
            pass

        # 3. Visibility & Target Safety
        if envelope.target_hint == TargetHint.BROADCAST:
            # Broadcasts are high risk, require explicit check (mock logic for J.3)
            # In a real system, this might check a "broadcast_enabled" flag
            # For now, we allow but flag it
            return PolicyDecision(
                allowed=True,
                reason="Broadcast allowed with constraints",
                constraints=["rate_limit_strict", "audit_logging"]
            )

        if envelope.target_hint == TargetHint.UNKNOWN:
            return PolicyDecision(
                allowed=False,
                reason="Target unknown",
                constraints=[]
            )

        # 4. Default Allow
        return PolicyDecision(
            allowed=True,
            reason="Policy checks passed",
            constraints=[]
        )