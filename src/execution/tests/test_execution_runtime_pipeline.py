from datetime import datetime, timedelta, timezone
from uuid import uuid4

from src.core.domain.execution_intent import ExecutionIntent
from src.core.domain.execution_result import ExecutionFailureType
from src.core.domain.resource import ResourceCost
from src.execution.domain.execution_job import DlqState, ExecutionJob, ExecutionJobState
from src.execution.queue.execution_queue import InMemoryExecutionQueue
from src.execution.results.execution_result_inbox import InMemoryExecutionResultInbox
from src.execution.results.result_dispatcher_service import ResultDispatcherConfig, ResultDispatcherService
from src.execution.retry.retry_scheduler import RetryPolicy, RetryScheduler
from src.execution.worker.execution_worker import ExecutionWorker, ExecutionWorkerConfig
from src.integration.normalizer import ResultNormalizer
from src.integration.registry import ExecutionAdapterRegistry


class SuccessTelegramAdapter:
    def execute(self, intent):
        return ResultNormalizer.success(
            effects=["message_sent"],
            costs={"api_calls": 1.0},
            observations={"message_id": 42},
        )


class EnvFailureAdapter:
    def execute(self, intent):
        return ResultNormalizer.failure(
            reason="telegram_5xx",
            failure_type=ExecutionFailureType.ENVIRONMENT,
        )


def _intent() -> ExecutionIntent:
    return ExecutionIntent(
        id=uuid4(),
        commitment_id=uuid4(),
        intention_id=uuid4(),
        persona_id=uuid4(),
        abstract_action="communicate",
        constraints={"platform": "telegram", "target_id": "chat-1", "text": "hello"},
        created_at=datetime.now(timezone.utc),
        reversible=False,
        risk_level=0.1,
        estimated_cost=ResourceCost(1.0, 1.0, 1),
    )


def test_worker_dispatcher_pipeline_applies_result_without_tick_dependency():
    queue = InMemoryExecutionQueue()
    inbox = InMemoryExecutionResultInbox()
    registry = ExecutionAdapterRegistry()
    registry.register("telegram", SuccessTelegramAdapter())

    intent = _intent()
    job_id = queue.enqueue(ExecutionJob.new(intent, "telegram:chat-1", {"energy_budget": -1.0}))

    worker = ExecutionWorker(
        config=ExecutionWorkerConfig(worker_id="w1"),
        queue=queue,
        inbox=inbox,
        adapter_registry=registry,
    )
    processed = worker.run_once()
    assert processed == 1
    assert queue.get(job_id).state == ExecutionJobState.COMPLETED

    applied = []
    dispatcher = ResultDispatcherService(
        config=ResultDispatcherConfig(dispatcher_id="d1"),
        inbox=inbox,
        apply_result=lambda envelope: applied.append(envelope),
    )
    assert dispatcher.run_once() == 1
    assert len(applied) == 1
    assert applied[0]["intent_id"] == intent.id


def test_environment_failure_retries_then_moves_to_dlq():
    queue = InMemoryExecutionQueue()
    inbox = InMemoryExecutionResultInbox()
    registry = ExecutionAdapterRegistry()
    registry.register("telegram", EnvFailureAdapter())

    intent = _intent()
    job_id = queue.enqueue(ExecutionJob.new(intent, "telegram:chat-1", {"energy_budget": -1.0}, max_attempts=2))

    worker = ExecutionWorker(
        config=ExecutionWorkerConfig(worker_id="w1", poll_interval_seconds=0.01),
        queue=queue,
        inbox=inbox,
        adapter_registry=registry,
        retry_scheduler=RetryScheduler(
            RetryPolicy(max_attempts=2, base_delay_seconds=0.01, factor=1.0, max_delay_seconds=0.01, jitter_ratio=0.0)
        ),
    )

    assert worker.run_once() == 1
    job = queue.get(job_id)
    assert job.state == ExecutionJobState.QUEUED
    assert job.attempt_count == 1

    # Force immediate retry for deterministic test.
    job.available_at = datetime.now(timezone.utc) - timedelta(seconds=1)

    assert worker.run_once() == 1
    job = queue.get(job_id)
    assert job.state == ExecutionJobState.DLQ
    assert job.dlq_state == DlqState.AWAITING_MANUAL_ACTION
    assert job.attempt_count == 2


def test_dlq_replay_creates_versioned_job():
    queue = InMemoryExecutionQueue()
    intent = _intent()
    job_id = queue.enqueue(ExecutionJob.new(intent, "telegram:chat-1", {}))

    leased = queue.lease(worker_id="w1", batch=1, visibility_timeout=timedelta(seconds=30))
    assert len(leased) == 1
    assert queue.move_to_dlq(job_id, "w1", DlqState.AWAITING_MANUAL_ACTION, "manual")

    replay = queue.replay_dlq(job_id, actor="operator")
    assert replay is not None
    assert replay.job_version == 2
    assert replay.parent_job_id == job_id
    assert queue.get(job_id).dlq_state == DlqState.REPLAYED
