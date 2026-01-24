from typing import Tuple, Optional
from src.core.domain.context import InternalContext
from src.core.domain.intention import Intention
from src.core.prompts.templates import THINK_PROMPT


class ThinkingService:
    """
    Encapsulates the logic of calling the LLM (mocked for Stage 2)
    and parsing the result into Thoughts and Intentions.
    """

    def think(self, context: InternalContext, name: str) -> Tuple[str, Optional[Intention]]:
        # 1. Prepare Prompt
        prompt = THINK_PROMPT.format(
            name=name,
            context_str=context.to_prompt_string()
        )

        # 2. Call LLM (MOCKED for Stage 2 as per "No external connections")
        # In real implementation, this calls LLaMA/Qwen
        internal_monologue, intention_data = self._mock_llm_inference(prompt, context)

        # 3. Parse Intention
        intention = None
        if intention_data and intention_data != "None":
            # Logic to determine priority/TTL would be here
            intention = Intention.create(
                type="generic_thought",
                content=intention_data,
                priority=1,
                ttl=600  # 10 minutes default
            )

        return internal_monologue, intention

    def _mock_llm_inference(self, prompt: str, context: InternalContext) -> Tuple[str, Optional[str]]:
        """
        Deterministic mock to satisfy "Fully runnable code" requirement without GPU/API.
        """
        if context.energy_level == "Exhausted":
            return "I am too tired to think clearly. I need to rest.", "rest"

        return "I am thinking about who I am. Silence is loud today.", None