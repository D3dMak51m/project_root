from datetime import datetime
from src.core.interfaces.thinking import ThinkingEngine
from src.core.context.internal import InternalContext
from src.core.domain.thought import ThoughtArtifact

class DeterministicThinkingEngine(ThinkingEngine):
    """
    NON-LLM implementation.
    Used to validate architecture and tests.
    """

    def think(self, context: InternalContext) -> ThoughtArtifact:
        mood = context.current_mood
        readiness = context.readiness_level

        summary = (
            f"I feel {mood}. "
            f"My readiness is {readiness}. "
            f"I have {context.active_intentions_count} pending impulses."
        )

        monologue = (
            f"Energy level feels {context.energy_level}. "
            f"Recent thoughts keep looping. "
            f"Nothing compels me strongly enough yet."
        )

        salient = list(context.recent_thoughts)

        return ThoughtArtifact(
            summary=summary,
            internal_monologue=monologue,
            salient_points=salient,
            emotional_tone=mood,
            created_at=datetime.utcnow()
        )