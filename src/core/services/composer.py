from src.core.domain.action import ActionProposal
from src.core.domain.persona import PersonaMask
from src.core.domain.content import ContentDraft

class ContentComposer:
    """
    Transforms an ActionProposal into platform-specific content
    using PersonaMask rules.
    Pure logic, no AI generation here (that would be in a separate generator if needed).
    """

    class ContentComposer:
        """
        MOCK COMPOSER (Stage 8).
        Transforms an ActionProposal into platform-specific content using PersonaMask rules.

        NOTE: This does NOT use LLM generation yet. It uses simple string manipulation
        to demonstrate the architectural flow. Real generation comes in Stage 9/10.
        """

        def compose(self, proposal: ActionProposal, mask: PersonaMask) -> ContentDraft:
            base_text = proposal.content

            # Mock Platform shaping
            if mask.platform == "twitter":
                base_text = base_text[:280]

            if mask.verbosity == "short":
                base_text = base_text.split(".")[0] + "."

            style = f"{mask.tone}, {mask.language}, {mask.verbosity}"

            return ContentDraft.create(
                action_id=proposal.id,
                platform=mask.platform,
                text=base_text,
                style=style
            )