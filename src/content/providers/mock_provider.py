from src.content.interfaces.llm_provider import GeneratedContent, LlmProvider
from typing import Optional


class MockLlmProvider(LlmProvider):
    def __init__(self, name: str = "mock", prefix: str = "Stub response:"):
        self.name = name
        self.prefix = prefix

    def generate(
        self,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
        trace_id: Optional[str] = None,
    ) -> GeneratedContent:
        snippet = " ".join(prompt.strip().split())[: max(0, max_tokens * 4)]
        return GeneratedContent(
            text=f"{self.prefix} {snippet}".strip(),
            provider=self.name,
            model=model,
            metadata={"trace_id": trace_id, "temperature": temperature},
        )
