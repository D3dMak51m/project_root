import os
from typing import Optional

from src.content.interfaces.llm_provider import GeneratedContent, LlmProvider


class AnthropicLlmProvider(LlmProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")

    def generate(
        self,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
        trace_id: Optional[str] = None,
    ) -> GeneratedContent:
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")
        try:
            import anthropic
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("anthropic package is not installed") from exc

        client = anthropic.Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        text = ""
        if getattr(response, "content", None):
            parts = []
            for chunk in response.content:
                if getattr(chunk, "text", None):
                    parts.append(chunk.text)
            text = "\n".join(parts)
        return GeneratedContent(
            text=text.strip(),
            provider="anthropic",
            model=model,
            metadata={"trace_id": trace_id},
        )

