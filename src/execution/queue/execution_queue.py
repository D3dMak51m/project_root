from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Dict, List, Optional
from uuid import UUID

from src.execution.domain.execution_job import DlqState, ExecutionJob, ExecutionJobState


class ExecutionQueue(ABC):
    @abstractmethod
    def enqueue(self, job: ExecutionJob) -> UUID:
        pass

    @abstractmethod
    def lease(self, worker_id: str, batch: int, visibility_timeout: timedelta) -> List[ExecutionJob]:
        pass

    @abstractmethod
    def heartbeat(self, job_id: UUID, worker_id: str, visibility_timeout: timedelta) -> bool:
        pass

    @abstractmethod
    def ack_success(self, job_id: UUID, worker_id: str) -> bool:
        pass

    @abstractmethod
    def release(
        self,
        job_id: UUID,
        worker_id: str,
        available_at: datetime,
        reason: str,
        decrement_attempt: bool = False,
    ) -> bool:
        pass

    @abstractmethod
    def move_to_dlq(self, job_id: UUID, worker_id: str, state: DlqState, reason: str) -> bool:
        pass

    @abstractmethod
    def reclaim_expired(self) -> int:
        pass

    @abstractmethod
    def get(self, job_id: UUID) -> Optional[ExecutionJob]:
        pass

    @abstractmethod
    def list_dlq(self, limit: int = 100) -> List[ExecutionJob]:
        pass

    @abstractmethod
    def replay_dlq(self, job_id: UUID, actor: str) -> Optional[ExecutionJob]:
        pass

    @abstractmethod
    def resolve_dlq(self, job_id: UUID, actor: str, state: DlqState) -> bool:
        pass

    @abstractmethod
    def depth(self) -> int:
        pass

    @abstractmethod
    def depth_by_context(self) -> Dict[str, int]:
        pass


class InMemoryExecutionQueue(ExecutionQueue):
    def __init__(self):
        self._jobs: Dict[UUID, ExecutionJob] = {}
        self._intent_index: Dict[UUID, UUID] = {}
        self._lock = Lock()

    def enqueue(self, job: ExecutionJob) -> UUID:
        with self._lock:
            existing = self._intent_index.get(job.intent.id)
            if existing:
                return existing
            self._jobs[job.id] = job
            self._intent_index[job.intent.id] = job.id
            return job.id

    def lease(self, worker_id: str, batch: int, visibility_timeout: timedelta) -> List[ExecutionJob]:
        now = datetime.now(timezone.utc)
        leased: List[ExecutionJob] = []
        with self._lock:
            candidates = [
                job
                for job in self._jobs.values()
                if job.state == ExecutionJobState.QUEUED and job.available_at <= now
            ]
            candidates.sort(key=lambda j: (-j.priority, j.created_at))
            for job in candidates[:batch]:
                job.state = ExecutionJobState.LEASED
                job.leased_by = worker_id
                job.lease_until = now + visibility_timeout
                job.attempt_count += 1
                job.updated_at = now
                leased.append(job)
        return leased

    def heartbeat(self, job_id: UUID, worker_id: str, visibility_timeout: timedelta) -> bool:
        now = datetime.now(timezone.utc)
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.state != ExecutionJobState.LEASED or job.leased_by != worker_id:
                return False
            job.lease_until = now + visibility_timeout
            job.updated_at = now
            return True

    def ack_success(self, job_id: UUID, worker_id: str) -> bool:
        now = datetime.now(timezone.utc)
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.state != ExecutionJobState.LEASED or job.leased_by != worker_id:
                return False
            job.state = ExecutionJobState.COMPLETED
            job.leased_by = None
            job.lease_until = None
            job.updated_at = now
            return True

    def release(
        self,
        job_id: UUID,
        worker_id: str,
        available_at: datetime,
        reason: str,
        decrement_attempt: bool = False,
    ) -> bool:
        now = datetime.now(timezone.utc)
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.state != ExecutionJobState.LEASED or job.leased_by != worker_id:
                return False
            job.state = ExecutionJobState.QUEUED
            job.leased_by = None
            job.lease_until = None
            job.available_at = available_at
            job.last_error = reason
            if decrement_attempt and job.attempt_count > 0:
                job.attempt_count -= 1
            job.updated_at = now
            return True

    def move_to_dlq(self, job_id: UUID, worker_id: str, state: DlqState, reason: str) -> bool:
        now = datetime.now(timezone.utc)
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.state != ExecutionJobState.LEASED or job.leased_by != worker_id:
                return False
            job.state = ExecutionJobState.DLQ
            job.dlq_state = state
            job.last_error = reason
            job.leased_by = None
            job.lease_until = None
            job.updated_at = now
            return True

    def reclaim_expired(self) -> int:
        now = datetime.now(timezone.utc)
        reclaimed = 0
        with self._lock:
            for job in self._jobs.values():
                if (
                    job.state == ExecutionJobState.LEASED
                    and job.lease_until is not None
                    and job.lease_until < now
                ):
                    job.state = ExecutionJobState.QUEUED
                    job.leased_by = None
                    job.lease_until = None
                    job.available_at = now
                    job.updated_at = now
                    reclaimed += 1
        return reclaimed

    def get(self, job_id: UUID) -> Optional[ExecutionJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def list_dlq(self, limit: int = 100) -> List[ExecutionJob]:
        with self._lock:
            items = [j for j in self._jobs.values() if j.state == ExecutionJobState.DLQ]
            items.sort(key=lambda j: j.updated_at, reverse=True)
            return items[:limit]

    def replay_dlq(self, job_id: UUID, actor: str) -> Optional[ExecutionJob]:
        now = datetime.now(timezone.utc)
        with self._lock:
            original = self._jobs.get(job_id)
            if not original or original.state != ExecutionJobState.DLQ:
                return None
            existing_id = self._intent_index.get(original.intent.id)
            if existing_id and existing_id in self._jobs:
                existing_job = self._jobs[existing_id]
                if existing_job.id != original.id and existing_job.state in (
                    ExecutionJobState.QUEUED,
                    ExecutionJobState.LEASED,
                ):
                    return existing_job
            original.dlq_state = DlqState.REPLAYED
            original.updated_at = now

            replay_job = ExecutionJob.new(
                intent=original.intent,
                context_domain=original.context_domain,
                reservation_delta=dict(original.reservation_delta),
                priority=original.priority,
                max_attempts=original.max_attempts,
            )
            replay_job.job_version = original.job_version + 1
            replay_job.parent_job_id = original.id
            replay_job.last_error = f"Replayed by {actor}"
            self._jobs[replay_job.id] = replay_job
            self._intent_index[replay_job.intent.id] = replay_job.id
            return replay_job

    def resolve_dlq(self, job_id: UUID, actor: str, state: DlqState) -> bool:
        now = datetime.now(timezone.utc)
        if state not in (DlqState.TERMINAL, DlqState.RESOLVED):
            return False
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.state != ExecutionJobState.DLQ:
                return False
            job.dlq_state = state
            job.updated_at = now
            job.last_error = f"{state.value} by {actor}"
            return True

    def depth(self) -> int:
        with self._lock:
            return len([j for j in self._jobs.values() if j.state == ExecutionJobState.QUEUED])

    def depth_by_context(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        with self._lock:
            for job in self._jobs.values():
                if job.state != ExecutionJobState.QUEUED:
                    continue
                out[job.context_domain] = out.get(job.context_domain, 0) + 1
        return out
