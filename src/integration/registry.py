from typing import Dict, Optional
from src.core.interfaces.execution_adapter import ExecutionAdapter
from src.interaction.domain.intent import InteractionIntent
from src.core.domain.execution_result import ExecutionResult
from src.integration.normalizer import ResultNormalizer


class ExecutionAdapterRegistry:
    """
    Runtime-only registry for resolving execution adapters.
    """

    def __init__(self):
        self._adapters: Dict[str, ExecutionAdapter] = {}

    def register(self, platform: str, adapter: ExecutionAdapter) -> None:
        self._adapters[platform] = adapter

    def resolve(self, intent: InteractionIntent) -> Optional[ExecutionAdapter]:
        # Logic to determine platform from intent metadata
        platform = intent.metadata.get("platform", "default")
        return self._adapters.get(platform)

    def execute_safe(self, intent: InteractionIntent) -> ExecutionResult:
        """
        Resolves and executes the intent, handling missing adapters safely.
        """
        adapter = self.resolve(intent)
        if not adapter:
            return ResultNormalizer.rejection(
                reason=f"No adapter found for platform: {intent.metadata.get('platform', 'unknown')}"
            )

        return adapter.execute(intent)