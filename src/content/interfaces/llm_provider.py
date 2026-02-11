from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class GeneratedContent:
    text: str
    provider: str
    model: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class LlmProvider(ABC):
    @abstractmethod
    def generate(
        self,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
        trace_id: Optional[str] = None,
    ) -> GeneratedContent:
        pass

