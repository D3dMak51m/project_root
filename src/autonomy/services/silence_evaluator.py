from src.autonomy.interfaces.silence_evaluator import SilenceEvaluator
from src.autonomy.domain.silence_decision import SilenceDecision
from src.autonomy.domain.initiative_decision import InitiativeDecision
from src.autonomy.domain.autonomy_mode import AutonomyMode
from src.interaction.domain.envelope import InteractionEnvelope
from src.autonomy.domain.autonomy_state import AutonomyState
from src.core.config.runtime_profile import RuntimeProfile
from src.autonomy.domain.silence_profile import SilenceProfile


class StandardSilenceEvaluator(SilenceEvaluator):
    """
    Deterministic evaluator for silence governance.
    Enforces pressure thresholds to prevent noise.
    """

    def evaluate(
            self,
            initiative: InitiativeDecision,
            envelope: InteractionEnvelope,
            autonomy: AutonomyState,
            profile: RuntimeProfile,
            silence_profile: SilenceProfile
    ) -> SilenceDecision:

        # 1. Initiative Check
        if initiative != InitiativeDecision.INITIATE:
            return SilenceDecision.SILENCE

        # 2. Autonomy Mode Check
        if autonomy.mode != AutonomyMode.READY:
            return SilenceDecision.SILENCE

        # 3. Determine Effective Threshold
        effective_threshold = silence_profile.priority_overrides.get(
            envelope.priority_hint,
            silence_profile.base_pressure_threshold
        )

        # 4. Pressure Check
        if autonomy.pressure_level < effective_threshold:
            return SilenceDecision.SILENCE

        # 5. Allow
        return SilenceDecision.ALLOW