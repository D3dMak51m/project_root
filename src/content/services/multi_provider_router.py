import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Sequence

from src.content.interfaces.llm_provider import GeneratedContent, LlmProvider


@dataclass(frozen=True)
class ProviderAttempt:
    provider: str
    ok: bool
    latency_ms: float
    error: str = ""


@dataclass(frozen=True)
class ProviderTrace:
    attempts: List[ProviderAttempt] = field(default_factory=list)


class MultiProviderRouter:
    """
    Provider failover order: primary -> secondary -> fallback.
    """

    def __init__(
        self,
        providers: Sequence[LlmProvider],
        on_attempt: Optional[Callable[[ProviderAttempt], None]] = None,
    ):
        self.providers = list(providers)
        self.on_attempt = on_attempt

    def generate(
        self,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
        trace_id: Optional[str] = None,
    ) -> tuple[GeneratedContent, ProviderTrace]:
        if not self.providers:
            raise RuntimeError("No LLM providers configured")

        attempts: List[ProviderAttempt] = []
        last_error: Optional[Exception] = None
        for provider in self.providers:
            started = time.monotonic()
            provider_name = provider.__class__.__name__
            try:
                generated = provider.generate(
                    prompt=prompt,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    trace_id=trace_id,
                )
                latency = (time.monotonic() - started) * 1000.0
                attempt = ProviderAttempt(provider=provider_name, ok=True, latency_ms=latency)
                attempts.append(attempt)
                if self.on_attempt:
                    self.on_attempt(attempt)
                return generated, ProviderTrace(attempts=attempts)
            except Exception as exc:
                latency = (time.monotonic() - started) * 1000.0
                attempt = ProviderAttempt(provider=provider_name, ok=False, latency_ms=latency, error=str(exc))
                attempts.append(attempt)
                if self.on_attempt:
                    self.on_attempt(attempt)
                last_error = exc

        raise RuntimeError(f"All providers failed: {last_error}") from last_error

