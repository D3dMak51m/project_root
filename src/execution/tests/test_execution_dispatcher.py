import pytest
from uuid import uuid4
from datetime import datetime, timezone
from src.autonomy.domain.execution_command import ExecutionCommand
from src.interaction.domain.envelope import InteractionEnvelope, TargetHint, PriorityHint, Visibility
from src.interaction.domain.intent import InteractionIntent, InteractionType
from src.execution.services.execution_dispatcher import StandardExecutionDispatcher
from src.integration.registry import ExecutionAdapterRegistry
from src.core.domain.execution_result import ExecutionStatus, ExecutionFailureType
from src.core.interfaces.execution_adapter import ExecutionAdapter
from src.core.domain.execution_result import ExecutionResult


# --- Mocks ---

class MockAdapter(ExecutionAdapter):
    def execute(self, intent: InteractionIntent) -> ExecutionResult:
        if intent.content == "fail_me":
            raise RuntimeError("Boom")
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            timestamp=datetime.now(timezone.utc),
            failure_type=ExecutionFailureType.NONE
        )


# --- Helpers ---

def create_command(content: str = "content") -> ExecutionCommand:
    intent = InteractionIntent(uuid4(), InteractionType.MESSAGE, content, {})
    envelope = InteractionEnvelope(intent, TargetHint.USER, PriorityHint.NORMAL, Visibility.EXTERNAL)
    return ExecutionCommand(uuid4(), envelope, datetime.now(timezone.utc))


# --- Tests ---

def test_dispatch_success():
    registry = ExecutionAdapterRegistry()
    # Register default adapter for None platform (default behavior of resolve)
    registry.register("default", MockAdapter())
    dispatcher = StandardExecutionDispatcher(registry)

    cmd = create_command("test")

    # Monkeypatch resolve to ensure our mock is returned regardless of metadata
    original_resolve = registry.resolve
    registry.resolve = lambda x: MockAdapter()

    result = dispatcher.dispatch(cmd)

    assert result.status == ExecutionStatus.SUCCESS
    registry.resolve = original_resolve


def test_dispatch_no_adapter():
    registry = ExecutionAdapterRegistry()
    dispatcher = StandardExecutionDispatcher(registry)

    cmd = create_command("test")
    result = dispatcher.dispatch(cmd)

    assert result.status == ExecutionStatus.FAILED
    assert result.failure_type == ExecutionFailureType.INTERNAL
    assert "No adapter found" in result.reason


def test_dispatch_adapter_exception():
    registry = ExecutionAdapterRegistry()

    class FailingAdapter(ExecutionAdapter):
        def execute(self, intent):
            raise RuntimeError("Crash")

    registry.resolve = lambda x: FailingAdapter()
    dispatcher = StandardExecutionDispatcher(registry)

    cmd = create_command("fail_me")
    result = dispatcher.dispatch(cmd)

    assert result.status == ExecutionStatus.FAILED
    assert result.failure_type == ExecutionFailureType.INTERNAL
    assert "Dispatcher caught exception" in result.reason
    assert "Crash" in result.reason