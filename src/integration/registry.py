from typing import Dict, Optional
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

    def resolve(self, intent: ExecutionIntent) -> Optional[ExecutionAdapter]:
        # Logic to determine platform from intent constraints
        # We look for 'platform' key in constraints
        platform = intent.constraints.get("platform", "default")
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