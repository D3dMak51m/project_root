from src.core.domain.execution_intent import ExecutionIntent
from src.core.domain.persona import PersonaMask


class TelegramPersonaProjectionService:
    """
    Pure service. Projects an ExecutionIntent into a Telegram-ready format
    based on the PersonaMask.
    Does NOT send messages.
    """

    def project(self, intent: ExecutionIntent, mask: PersonaMask) -> dict:
        """
        Returns a dictionary of constraints/payloads ready for the Telegram adapter.
        Applies persona-specific formatting, tone, and safety checks.
        """
        # 1. Extract base content
        # Assuming intent.constraints holds the raw 'text' or 'content'
        # In a real system, this might come from a ContentDraft object
        raw_text = intent.constraints.get("text", "")

        # 2. Apply Persona Tone/Style (Mock logic for T3)
        # In production, this would use an LLM or template engine
        formatted_text = raw_text

        if mask.tone == "formal":
            formatted_text = f"{formatted_text}"  # Placeholder for formalizing
        elif mask.tone == "casual":
            formatted_text = f"{formatted_text}"  # Placeholder for casualizing

        # 3. Apply Safety Formatting (HTML escaping)
        # Simple replacement for demo; use a library like 'html' in prod
        safe_text = formatted_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        # 4. Construct Payload
        return {
            "platform": "telegram",
            "target_id": intent.constraints.get("target_id"),
            "text": safe_text,
            "parse_mode": "HTML",  # Enforce safe HTML
            "persona_id": str(mask.id),
            "display_name": mask.display_name
        }