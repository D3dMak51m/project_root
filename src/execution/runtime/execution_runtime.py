import threading
from dataclasses import dataclass
from typing import Optional

from src.core.orchestration.strategic_orchestrator import StrategicOrchestrator
from src.execution.idempotency.idempotency_store import IdempotencyStore, InMemoryIdempotencyStore
from src.execution.limits.rate_limiter import InMemorySlidingRateLimiter
from src.execution.queue.execution_queue import ExecutionQueue
from src.execution.results.execution_result_inbox import (
    ExecutionResultInbox,
    InMemoryExecutionResultInbox,
)
from src.execution.results.result_dispatcher_service import (
    ResultDispatcherConfig,
    ResultDispatcherService,
)
from src.execution.retry.retry_scheduler import RetryPolicy, RetryScheduler
from src.execution.safety.circuit_breaker import InMemoryCircuitBreaker
from src.execution.safety.postgres_safety_store import PostgresExecutionSafetyStore
from src.execution.worker.execution_worker import ExecutionWorker, ExecutionWorkerConfig
from src.execution.worker.worker_heartbeat import InMemoryWorkerHeartbeatStore, WorkerHeartbeatStore
from src.execution.worker.worker_supervisor import WorkerSupervisor
from src.integration.registry import ExecutionAdapterRegistry


@dataclass(frozen=True)
class ExecutionRuntimeConfig:
    worker_count: int = 1
    worker_batch_size: int = 10
    worker_poll_interval_seconds: float = 0.2
    worker_visibility_timeout_seconds: int = 30
    worker_stale_in_progress_seconds: int = 120
    dispatcher_batch_size: int = 50
    dispatcher_poll_interval_seconds: float = 0.2
    dispatcher_visibility_timeout_seconds: int = 10
    result_apply_sla_ms: int = 1000
    watchdog_interval_seconds: float = 1.0
    start_embedded_workers: bool = True


class ExecutionRuntime:
    """
    In-process runtime that wires queue -> workers -> result dispatcher.
    """

    def __init__(
        self,
        orchestrator: StrategicOrchestrator,
        adapter_registry: ExecutionAdapterRegistry,
        queue: ExecutionQueue,
        inbox: Optional[ExecutionResultInbox] = None,
        config: Optional[ExecutionRuntimeConfig] = None,
        retry_policy: Optional[RetryPolicy] = None,
        rate_limiter: Optional[InMemorySlidingRateLimiter] = None,
        circuit_breaker: Optional[InMemoryCircuitBreaker] = None,
        idempotency_store: Optional[IdempotencyStore] = None,
        heartbeat_store: Optional[WorkerHeartbeatStore] = None,
        safety_store: Optional[PostgresExecutionSafetyStore] = None,
    ):
        self.orchestrator = orchestrator
        self.adapter_registry = adapter_registry
        self.queue = queue
        self.inbox = inbox or InMemoryExecutionResultInbox()
        self.config = config or ExecutionRuntimeConfig()
        self.retry_scheduler = RetryScheduler(retry_policy or RetryPolicy())
        self.rate_limiter = rate_limiter or InMemorySlidingRateLimiter()
        self.circuit_breaker = circuit_breaker or InMemoryCircuitBreaker()
        self.idempotency_store = idempotency_store or InMemoryIdempotencyStore()
        self.heartbeat_store = heartbeat_store or InMemoryWorkerHeartbeatStore()
        self.safety_store = safety_store

        self.dispatcher = ResultDispatcherService(
            config=ResultDispatcherConfig(
                dispatcher_id="dispatcher-1",
                batch_size=self.config.dispatcher_batch_size,
                poll_interval_seconds=self.config.dispatcher_poll_interval_seconds,
                visibility_timeout_seconds=self.config.dispatcher_visibility_timeout_seconds,
                result_apply_sla_ms=self.config.result_apply_sla_ms,
            ),
            inbox=self.inbox,
            apply_result=self.orchestrator.post_execution_pipeline,
        )

        self._dispatcher_thread: Optional[threading.Thread] = None
        self.supervisor = WorkerSupervisor(self._build_workers())
        self._started = False

    def _build_workers(self):
        workers = []
        for idx in range(self.config.worker_count):
            worker = ExecutionWorker(
                config=ExecutionWorkerConfig(
                    worker_id=f"worker-{idx + 1}",
                    batch_size=self.config.worker_batch_size,
                    poll_interval_seconds=self.config.worker_poll_interval_seconds,
                    visibility_timeout_seconds=self.config.worker_visibility_timeout_seconds,
                    stale_in_progress_seconds=self.config.worker_stale_in_progress_seconds,
                ),
                queue=self.queue,
                inbox=self.inbox,
                adapter_registry=self.adapter_registry,
                retry_scheduler=self.retry_scheduler,
                rate_limiter=self.rate_limiter,
                circuit_breaker=self.circuit_breaker,
                idempotency_store=self.idempotency_store,
                heartbeat_store=self.heartbeat_store,
                push_notify=self.dispatcher.notify,
                on_circuit_transition=self.safety_store.record_transition if self.safety_store else None,
            )
            workers.append(worker)
        return workers

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._dispatcher_thread = threading.Thread(target=self.dispatcher.run_forever, daemon=True)
        self._dispatcher_thread.start()
        if self.config.start_embedded_workers:
            self.supervisor.start()
            self.supervisor.start_watchdog(self.config.watchdog_interval_seconds)
        if self.safety_store:
            self.safety_store.record_rate_limit_snapshot(self.rate_limiter.snapshot())

    def stop(self) -> None:
        if not self._started:
            return
        self.dispatcher.stop()
        self.supervisor.stop()
        if self._dispatcher_thread:
            self._dispatcher_thread.join(timeout=2.0)
        if self.safety_store:
            self.safety_store.record_rate_limit_snapshot(self.rate_limiter.snapshot())
        self._started = False
