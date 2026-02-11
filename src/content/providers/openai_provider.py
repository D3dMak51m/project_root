import os
from typing import Optional

from src.content.interfaces.llm_provider import GeneratedContent, LlmProvider


class OpenAILlmProvider(LlmProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")

    def generate(
        self,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
        trace_id: Optional[str] = None,
    ) -> GeneratedContent:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        try:
            from openai import OpenAI
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("openai package is not installed") from exc

        client = OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        text = ""
        if response.choices and response.choices[0].message:
            text = response.choices[0].message.content or ""
        return GeneratedContent(
            text=text.strip(),
            provider="openai",
            model=model,
            metadata={"trace_id": trace_id},
        )

