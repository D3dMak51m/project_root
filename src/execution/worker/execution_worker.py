import threading
import time
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from src.content.services.content_generation_service import ContentGenerationService
from src.core.domain.execution_result import ExecutionFailureType, ExecutionResult, ExecutionStatus
from src.execution.logging.structured_runtime_logger import StructuredRuntimeLogger
from src.execution.limits.adaptive_rate_controller import AdaptiveRateController
from src.integration.registry import ExecutionAdapterRegistry
from src.integration.normalizer import ResultNormalizer
from src.execution.domain.execution_job import DlqState
from src.execution.domain.execution_result_envelope import ExecutionResultEnvelope
from src.execution.idempotency.idempotency_store import (
    IdempotencyState,
    IdempotencyStore,
    InMemoryIdempotencyStore,
)
from src.execution.limits.rate_limiter import InMemorySlidingRateLimiter
from src.execution.queue.execution_queue import ExecutionQueue
from src.execution.results.execution_result_inbox import ExecutionResultInbox
from src.execution.retry.retry_scheduler import RetryPolicy, RetryScheduler
from src.execution.safety.circuit_breaker import InMemoryCircuitBreaker
from src.execution.worker.worker_heartbeat import (
    InMemoryWorkerHeartbeatStore,
    WorkerHeartbeatStore,
)
from src.infrastructure.observability.anomaly_hook import AnomalyHook, NoopAnomalyHook


@dataclass(frozen=True)
class ExecutionWorkerConfig:
    worker_id: str
    batch_size: int = 10
    poll_interval_seconds: float = 0.2
    visibility_timeout_seconds: int = 30
    lease_heartbeat_interval_seconds: int = 10
    stale_in_progress_seconds: int = 120
    reclaim_interval_seconds: float = 1.0


class ExecutionWorker:
    def __init__(
        self,
        config: ExecutionWorkerConfig,
        queue: ExecutionQueue,
        inbox: ExecutionResultInbox,
        adapter_registry: ExecutionAdapterRegistry,
        retry_scheduler: Optional[RetryScheduler] = None,
        rate_limiter: Optional[InMemorySlidingRateLimiter] = None,
        circuit_breaker: Optional[InMemoryCircuitBreaker] = None,
        idempotency_store: Optional[IdempotencyStore] = None,
        heartbeat_store: Optional[WorkerHeartbeatStore] = None,
        push_notify: Optional[Callable[[], None]] = None,
        on_circuit_transition: Optional[Callable[[Any], None]] = None,
        content_generation_service: Optional[ContentGenerationService] = None,
        adaptive_rate_controller: Optional[AdaptiveRateController] = None,
        anomaly_hook: Optional[AnomalyHook] = None,
        structured_logger: Optional[StructuredRuntimeLogger] = None,
    ):
        self.config = config
        self.queue = queue
        self.inbox = inbox
        self.adapter_registry = adapter_registry
        self.retry_scheduler = retry_scheduler or RetryScheduler(RetryPolicy())
        self.rate_limiter = rate_limiter or InMemorySlidingRateLimiter()
        self.circuit_breaker = circuit_breaker or InMemoryCircuitBreaker()
        self.idempotency_store = idempotency_store or InMemoryIdempotencyStore()
        self.heartbeat_store = heartbeat_store or InMemoryWorkerHeartbeatStore()
        self.push_notify = push_notify
        self.on_circuit_transition = on_circuit_transition
        self.content_generation_service = content_generation_service
        self.adaptive_rate_controller = adaptive_rate_controller
        self.anomaly_hook = anomaly_hook or NoopAnomalyHook()
        self.structured_logger = structured_logger

        self._stop_event = threading.Event()
        self._last_reclaim = datetime.now(timezone.utc)

    def run_forever(self) -> None:
        while not self._stop_event.is_set():
            self.run_once()
            time.sleep(self.config.poll_interval_seconds)
        self.heartbeat_store.beat(self.config.worker_id, status="stopped")

    def stop(self) -> None:
        self._stop_event.set()

    def run_once(self) -> int:
        if self._stop_event.is_set():
            return 0
        now = datetime.now(timezone.utc)
        self.heartbeat_store.beat(self.config.worker_id, status="alive")

        if (now - self._last_reclaim).total_seconds() >= self.config.reclaim_interval_seconds:
            self.queue.reclaim_expired()
            self.inbox.reclaim_expired()
            self._last_reclaim = now

        jobs = self.queue.lease(
            worker_id=self.config.worker_id,
            batch=self.config.batch_size,
            visibility_timeout=timedelta(seconds=self.config.visibility_timeout_seconds),
        )
        processed = 0
        for job in jobs:
            self._handle_job(job)
            processed += 1

        if self.on_circuit_transition:
            for transition in self.circuit_breaker.drain_transitions():
                self.on_circuit_transition(transition)
        return processed

    def _handle_job(self, job) -> None:
        now = datetime.now(timezone.utc)
        platform = str(job.intent.constraints.get("platform", "default"))
        target_id = str(job.intent.constraints.get("target_id", "unknown"))
        chat_key = f"{platform}:{target_id}"
        queue_lag = float(self.queue.depth()) if hasattr(self.queue, "depth") else 0.0
        self._log(
            "WORKER_JOB_START",
            worker_id=self.config.worker_id,
            job_id=str(job.id),
            intent_id=str(job.intent.id),
            context_domain=job.context_domain,
            queue_lag=queue_lag,
        )

        if self.adaptive_rate_controller:
            adaptive_delay = self.adaptive_rate_controller.pre_send_delay(platform, queue_lag=queue_lag)
            if adaptive_delay > 0:
                self.queue.release(
                    job.id,
                    self.config.worker_id,
                    available_at=now + timedelta(seconds=adaptive_delay),
                    reason="Adaptive throttling",
                    decrement_attempt=True,
                )
                self._log(
                    "WORKER_ADAPTIVE_THROTTLE",
                    worker_id=self.config.worker_id,
                    job_id=str(job.id),
                    intent_id=str(job.intent.id),
                    context_domain=job.context_domain,
                    delay_seconds=adaptive_delay,
                )
                return

        if not self.circuit_breaker.allow(platform, now=now):
            self.queue.release(
                job.id,
                self.config.worker_id,
                available_at=now + timedelta(seconds=1),
                reason="Circuit open",
                decrement_attempt=True,
            )
            self._log(
                "WORKER_CIRCUIT_OPEN",
                worker_id=self.config.worker_id,
                job_id=str(job.id),
                intent_id=str(job.intent.id),
                context_domain=job.context_domain,
                platform=platform,
            )
            return

        allowed, retry_after = self.rate_limiter.allow(chat_key, now=now)
        if not allowed:
            self.queue.release(
                job.id,
                self.config.worker_id,
                available_at=now + timedelta(seconds=retry_after),
                reason="Rate limited",
                decrement_attempt=True,
            )
            self._log(
                "WORKER_RATE_LIMITED",
                worker_id=self.config.worker_id,
                job_id=str(job.id),
                intent_id=str(job.intent.id),
                context_domain=job.context_domain,
                retry_after=retry_after,
            )
            return

        idem_state = self.idempotency_store.begin(job.intent.id)
        if idem_state == IdempotencyState.DONE:
            self.queue.ack_success(job.id, self.config.worker_id)
            self._log(
                "WORKER_IDEMPOTENT_DONE",
                worker_id=self.config.worker_id,
                job_id=str(job.id),
                intent_id=str(job.intent.id),
                context_domain=job.context_domain,
            )
            return

        if idem_state == IdempotencyState.IN_PROGRESS:
            record = self.idempotency_store.get(job.intent.id)
            if record and (now - record.updated_at).total_seconds() > self.config.stale_in_progress_seconds:
                result = ResultNormalizer.failure(
                    reason="Unknown execution outcome after stale in-progress lock",
                    failure_type=ExecutionFailureType.ENVIRONMENT,
                )
                self.queue.move_to_dlq(
                    job.id,
                    self.config.worker_id,
                    state=DlqState.AWAITING_MANUAL_ACTION,
                    reason=result.reason,
                )
                self._publish_terminal_result(job, result)
                self._log(
                    "WORKER_STALE_IN_PROGRESS_DLQ",
                    worker_id=self.config.worker_id,
                    job_id=str(job.id),
                    intent_id=str(job.intent.id),
                    context_domain=job.context_domain,
                )
            else:
                self.queue.release(
                    job.id,
                    self.config.worker_id,
                    available_at=now + timedelta(seconds=1),
                    reason="Execution already in progress",
                    decrement_attempt=True,
                )
            return

        runtime_intent = job.intent
        if (
            self.content_generation_service
            and bool(job.intent.constraints.get("content_generation_required"))
        ):
            try:
                runtime_intent, content_outcome = self.content_generation_service.apply_to_intent(
                    job.intent,
                    trace_id=str(job.intent.id),
                )
                self._log(
                    "CONTENT_GENERATED",
                    worker_id=self.config.worker_id,
                    job_id=str(job.id),
                    intent_id=str(job.intent.id),
                    context_domain=job.context_domain,
                    provider=content_outcome.provider,
                    fallback_used=content_outcome.fallback_used,
                    decision=content_outcome.decision,
                    error=content_outcome.error,
                )
            except Exception as exc:
                fallback_constraints = dict(job.intent.constraints)
                fallback_constraints["text"] = str(
                    job.intent.constraints.get(
                        "fallback_template",
                        "I received your message. Please try again in a different way.",
                    )
                )
                fallback_constraints["content_generation_meta"] = {
                    "provider": "fallback",
                    "fallback_used": True,
                    "decision": "error",
                    "error": str(exc),
                }
                runtime_intent = replace(job.intent, constraints=fallback_constraints)
                self._log(
                    "CONTENT_FALLBACK",
                    worker_id=self.config.worker_id,
                    job_id=str(job.id),
                    intent_id=str(job.intent.id),
                    context_domain=job.context_domain,
                    error=str(exc),
                )

        try:
            self.queue.heartbeat(
                job.id,
                self.config.worker_id,
                visibility_timeout=timedelta(seconds=self.config.visibility_timeout_seconds),
            )
            result = self.adapter_registry.execute_safe(runtime_intent)
        except Exception as exc:
            result = ResultNormalizer.failure(
                reason=f"Worker caught exception: {exc}",
                failure_type=ExecutionFailureType.INTERNAL,
            )
        finally:
            self.queue.heartbeat(
                job.id,
                self.config.worker_id,
                visibility_timeout=timedelta(seconds=self.config.visibility_timeout_seconds),
            )

        if result.status == ExecutionStatus.SUCCESS:
            self.idempotency_store.complete(job.intent.id, metadata=result.observations)
            self.queue.ack_success(job.id, self.config.worker_id)
            self.circuit_breaker.record_success(platform, now=now)
            if self.adaptive_rate_controller:
                self.adaptive_rate_controller.record_result(platform, result)
            self._emit_anomaly(result, job.context_domain)
            self._publish_terminal_result(job, result)
            self._log(
                "WORKER_JOB_SUCCESS",
                worker_id=self.config.worker_id,
                job_id=str(job.id),
                intent_id=str(job.intent.id),
                context_domain=job.context_domain,
            )
            return

        if result.failure_type == ExecutionFailureType.ENVIRONMENT:
            self.circuit_breaker.record_failure(platform, now=now)
            if self.adaptive_rate_controller:
                self.adaptive_rate_controller.record_result(platform, result)
            self._emit_anomaly(result, job.context_domain)
            if self.retry_scheduler.should_retry(job.attempt_count):
                self.idempotency_store.clear_in_progress(job.intent.id)
                retry_at = self.retry_scheduler.next_retry_at(job.attempt_count, now=now)
                self.queue.release(
                    job.id,
                    self.config.worker_id,
                    available_at=retry_at,
                    reason=result.reason or "Environment failure",
                )
                self._log(
                    "WORKER_JOB_RETRY",
                    worker_id=self.config.worker_id,
                    job_id=str(job.id),
                    intent_id=str(job.intent.id),
                    context_domain=job.context_domain,
                    retry_at=retry_at.isoformat(),
                    reason=result.reason,
                )
                return

            self.idempotency_store.clear_in_progress(job.intent.id)
            self.queue.move_to_dlq(
                job.id,
                self.config.worker_id,
                state=DlqState.AWAITING_MANUAL_ACTION,
                reason=result.reason or "Max retries exceeded",
            )
            self._log(
                "WORKER_JOB_DLQ",
                worker_id=self.config.worker_id,
                job_id=str(job.id),
                intent_id=str(job.intent.id),
                context_domain=job.context_domain,
                reason=result.reason,
            )
            self._publish_terminal_result(job, result)
            return

        self.idempotency_store.clear_in_progress(job.intent.id)
        self.queue.ack_success(job.id, self.config.worker_id)
        if self.adaptive_rate_controller:
            self.adaptive_rate_controller.record_result(platform, result)
        self._emit_anomaly(result, job.context_domain)
        self._publish_terminal_result(job, result)
        self._log(
            "WORKER_JOB_NON_RETRY_FAILURE",
            worker_id=self.config.worker_id,
            job_id=str(job.id),
            intent_id=str(job.intent.id),
            context_domain=job.context_domain,
            reason=result.reason,
        )

    def _publish_terminal_result(self, job, result: ExecutionResult) -> None:
        self.inbox.append(
            ExecutionResultEnvelope(
                job_id=job.id,
                intent_id=job.intent.id,
                context_domain=job.context_domain,
                reservation_delta=job.reservation_delta,
                result=result,
            )
        )
        if self.push_notify:
            self.push_notify()

    def _emit_anomaly(self, result: ExecutionResult, context_domain: str) -> None:
        try:
            self.anomaly_hook.on_outbound(result, context_domain=context_domain)
        except Exception:
            return

    def _log(self, event_type: str, **fields: Any) -> None:
        if not self.structured_logger:
            return
        self.structured_logger.emit(event_type=event_type, **fields)
