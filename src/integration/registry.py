from typing import Any, Dict, Optional
from datetime import datetime, timezone
from src.core.interfaces.execution_adapter import ExecutionAdapter
from src.core.domain.execution_intent import ExecutionIntent
from src.core.domain.execution_result import ExecutionResult
from src.integration.normalizer import ResultNormalizer


class ExecutionAdapterRegistry:
    """
    Runtime-only registry for resolving execution adapters.
    """
    _instance = None

    def __init__(self):
        self._adapters: Dict[str, ExecutionAdapter] = {}

    @classmethod
    def get_global(cls) -> 'ExecutionAdapterRegistry':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, platform: str, adapter: ExecutionAdapter) -> None:
        self._adapters[platform] = adapter

    def resolve(self, intent: Any) -> Optional[ExecutionAdapter]:
        """
        Resolve adapter for both ExecutionIntent (constraints-based) and
        interaction-style intents used by legacy dispatcher tests.
        """
        platform = "default"

        constraints = getattr(intent, "constraints", None)
        if isinstance(constraints, dict):
            platform = str(constraints.get("platform", "default"))
        else:
            metadata = getattr(intent, "metadata", None)
            if isinstance(metadata, dict):
                platform = str(metadata.get("platform", "default"))

        return self._adapters.get(platform)

    def execute_safe(self, intent: ExecutionIntent) -> ExecutionResult:
        """
        Resolves and executes the intent, handling missing adapters safely.
        """
        adapter = self.resolve(intent)
        if not adapter:
            return ResultNormalizer.rejection(
                reason=f"No adapter found for platform: {intent.constraints.get('platform', 'unknown')}"
            )

        return adapter.execute(intent)
