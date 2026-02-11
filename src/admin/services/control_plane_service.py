from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from src.admin.domain.admin_mutation_audit import AdminMutationAudit
from src.admin.store.mutation_audit_store import MutationAuditStore
from src.core.domain.execution_intent import ExecutionIntent
from src.core.domain.execution_result import ExecutionFailureType
from src.core.orchestration.strategic_orchestrator import StrategicOrchestrator
from src.execution.domain.execution_job import DlqState, ExecutionJob
from src.execution.queue.execution_queue import ExecutionQueue
from src.integration.normalizer import ResultNormalizer
from src.memory.store.counterfactual_memory_store import CounterfactualMemoryStore
from src.memory.store.memory_store import MemoryStore
from src.world.store.world_observation_store import WorldObservationStore


class AdminControlPlaneService:
    def __init__(
        self,
        orchestrator: StrategicOrchestrator,
        execution_queue: ExecutionQueue,
        world_store: WorldObservationStore,
        memory_store: MemoryStore,
        counterfactual_store: CounterfactualMemoryStore,
        mutation_audit_store: Optional[MutationAuditStore] = None,
    ):
        self.orchestrator = orchestrator
        self.execution_queue = execution_queue
        self.world_store = world_store
        self.memory_store = memory_store
        self.counterfactual_store = counterfactual_store
        self.mutation_audit_store = mutation_audit_store or MutationAuditStore()
        self._global_pause = False
        self._panic_mode = False
        self._disabled_contexts: set[str] = set()
        self._disabled_platforms: set[str] = set()

    def list_contexts(self) -> List[Dict[str, Any]]:
        queue_depths = self.execution_queue.depth_by_context()
        pending_feedback = getattr(self.orchestrator, "_pending_feedback_by_context", {})
        pending_meta = getattr(self.orchestrator, "_pending_execution_meta", {})
        latest_by_context: Dict[str, str] = {}
        for meta in pending_meta.values():
            context_domain = str(meta.get("context_domain", "unknown"))
            intent = meta.get("intent")
            if intent:
                latest_by_context[context_domain] = str(intent.id)

        items: List[Dict[str, Any]] = []
        runtimes = getattr(self.orchestrator, "_runtimes", {})
        for runtime in runtimes.values():
            context_domain = runtime.context.domain
            items.append(
                {
                    "context_domain": context_domain,
                    "active": bool(runtime.active),
                    "tick_count": int(runtime.tick_count),
                    "starvation_score": float(runtime.starvation_score),
                    "last_win_tick": int(runtime.last_win_tick),
                    "queue_depth": int(queue_depths.get(context_domain, 0)),
                    "pending_feedback": int(len(pending_feedback.get(context_domain, []))),
                    "last_intent_id": latest_by_context.get(context_domain),
                    "disabled": context_domain in self._disabled_contexts,
                }
            )
        items.sort(key=lambda x: x["context_domain"])
        return items

    def get_memory_view(self, context_domain: str, limit: int = 100) -> Dict[str, Any]:
        observations = self._world_by_context(context_domain, limit)
        events = [e for e in self.memory_store.list_all() if e.context_domain == context_domain][-limit:]
        counterfactuals = self.counterfactual_store.list_by_context(context_domain)[-limit:]
        return {
            "context_domain": context_domain,
            "observation_count": len(observations),
            "execution_events_count": len(events),
            "counterfactual_count": len(counterfactuals),
            "observations": observations,
            "execution_events": events,
            "counterfactual_events": counterfactuals,
        }

    def get_budget_view(self, limit: int = 100) -> Dict[str, Any]:
        history = self.orchestrator.budget_ledger.get_history()
        recent = history[-limit:]
        budget = getattr(self.orchestrator, "_budget")
        return {
            "energy_budget": budget.energy_budget,
            "attention_budget": budget.attention_budget,
            "execution_slots": budget.execution_slots,
            "last_updated": budget.last_updated,
            "recent_events": recent,
        }

    def list_dlq(self, limit: int = 100) -> List[Dict[str, Any]]:
        rows = self.execution_queue.list_dlq(limit=limit)
        return [self._job_summary(job) for job in rows]

    def replay_dlq(self, job_id: UUID, actor: str, role: str) -> Optional[Dict[str, Any]]:
        before = self.execution_queue.get(job_id)
        replay = self.execution_queue.replay_dlq(job_id, actor=actor)
        if not replay:
            return None
        after = self.execution_queue.get(job_id)
        self._audit(
            actor=actor,
            role=role,
            action="dlq_replay",
            target=str(job_id),
            before=self._job_summary(before) if before else {},
            after=self._job_summary(after) if after else {},
            metadata={"replay_job_id": str(replay.id)},
        )
        return self._job_summary(replay)

    def resolve_dlq(self, job_id: UUID, target_state: DlqState, actor: str, role: str) -> bool:
        before = self.execution_queue.get(job_id)
        ok = self.execution_queue.resolve_dlq(job_id, actor=actor, state=target_state)
        after = self.execution_queue.get(job_id)
        if ok:
            self._audit(
                actor=actor,
                role=role,
                action="dlq_resolve",
                target=str(job_id),
                before=self._job_summary(before) if before else {},
                after=self._job_summary(after) if after else {},
                metadata={"target_state": target_state.value},
            )
        return ok

    def set_global_pause(self, paused: bool, actor: str, role: str) -> None:
        before = {"paused": self._global_pause}
        self._global_pause = paused
        for runtime in getattr(self.orchestrator, "_runtimes", {}).values():
            runtime.active = not paused
        self._audit(
            actor=actor,
            role=role,
            action="global_pause_toggle",
            target="global",
            before=before,
            after={"paused": self._global_pause},
        )

    def set_panic_mode(self, enabled: bool, actor: str, role: str) -> None:
        before = {"panic_mode": self._panic_mode}
        self._panic_mode = enabled
        if hasattr(self.orchestrator, "set_panic_mode"):
            self.orchestrator.set_panic_mode(enabled)
        if enabled:
            self._disabled_platforms.add("telegram")
            if hasattr(self.orchestrator, "set_platform_enabled"):
                self.orchestrator.set_platform_enabled("telegram", False)
        else:
            self._disabled_platforms.discard("telegram")
            if hasattr(self.orchestrator, "set_platform_enabled"):
                self.orchestrator.set_platform_enabled("telegram", True)
        self._audit(
            actor=actor,
            role=role,
            action="panic_mode_toggle",
            target="global",
            before=before,
            after={"panic_mode": self._panic_mode},
        )

    def set_context_enabled(self, context_domain: str, enabled: bool, actor: str, role: str) -> bool:
        before = {"enabled": context_domain not in self._disabled_contexts}
        runtime = None
        for value in getattr(self.orchestrator, "_runtimes", {}).values():
            if value.context.domain == context_domain:
                runtime = value
                break
        if not runtime:
            return False
        runtime.active = enabled
        if enabled:
            self._disabled_contexts.discard(context_domain)
        else:
            self._disabled_contexts.add(context_domain)
        self._audit(
            actor=actor,
            role=role,
            action="context_enable_toggle",
            target=context_domain,
            before=before,
            after={"enabled": enabled},
        )
        return True

    def set_platform_enabled(self, platform: str, enabled: bool, actor: str, role: str) -> None:
        before = {"enabled": platform not in self._disabled_platforms}
        if enabled:
            self._disabled_platforms.discard(platform)
        else:
            self._disabled_platforms.add(platform)
        if hasattr(self.orchestrator, "set_platform_enabled"):
            self.orchestrator.set_platform_enabled(platform, enabled)
        self._audit(
            actor=actor,
            role=role,
            action="platform_enable_toggle",
            target=platform,
            before=before,
            after={"enabled": enabled},
        )

    def inject_intent(
        self,
        intent: ExecutionIntent,
        context_domain: str,
        actor: str,
        role: str,
        max_attempts: int = 5,
    ) -> UUID:
        job = ExecutionJob.new(
            intent=intent,
            context_domain=context_domain,
            reservation_delta={},
            max_attempts=max_attempts,
        )
        job_id = self.execution_queue.enqueue(job)
        self._audit(
            actor=actor,
            role=role,
            action="inject_intent",
            target=context_domain,
            metadata={"job_id": str(job_id), "intent_id": str(intent.id)},
        )
        return job_id

    def simulate_outcome(
        self,
        intent_id: UUID,
        context_domain: str,
        outcome: str,
        actor: str,
        role: str,
        reason: str = "",
    ) -> None:
        if outcome == "success":
            result = ResultNormalizer.success(
                effects=["simulated_success"],
                costs={},
                observations={"simulated": True},
            )
        elif outcome == "failure":
            result = ResultNormalizer.failure(
                reason=reason or "Simulated failure",
                failure_type=ExecutionFailureType.ENVIRONMENT,
            )
        else:
            result = ResultNormalizer.rejection(reason=reason or "Simulated rejection")

        self.orchestrator.post_execution_pipeline(
            {
                "intent_id": intent_id,
                "context_domain": context_domain,
                "reservation_delta": {},
                "result": result,
            }
        )
        self._audit(
            actor=actor,
            role=role,
            action="simulate_outcome",
            target=context_domain,
            metadata={"intent_id": str(intent_id), "outcome": outcome},
        )

    def get_mutation_audit(self, limit: int = 200) -> List[AdminMutationAudit]:
        return self.mutation_audit_store.list_recent(limit=limit)

    def _world_by_context(self, context_domain: str, limit: int) -> List[Any]:
        if hasattr(self.world_store, "list_by_context"):
            return self.world_store.list_by_context(context_domain, limit=limit)
        values = [obs for obs in self.world_store.list_all() if obs.context_domain == context_domain]
        return values[-limit:]

    def _job_summary(self, job: Optional[ExecutionJob]) -> Dict[str, Any]:
        if not job:
            return {}
        return {
            "job_id": str(job.id),
            "intent_id": str(job.intent.id),
            "context_domain": job.context_domain,
            "state": job.state.value,
            "attempt_count": job.attempt_count,
            "max_attempts": job.max_attempts,
            "dlq_state": job.dlq_state.value if job.dlq_state else None,
            "job_version": job.job_version,
            "parent_job_id": str(job.parent_job_id) if job.parent_job_id else None,
            "last_error": job.last_error,
        }

    def _audit(
        self,
        actor: str,
        role: str,
        action: str,
        target: str,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.mutation_audit_store.append(
            AdminMutationAudit(
                id=uuid4(),
                actor=actor,
                role=role,
                action=action,
                target=target,
                at=datetime.now(timezone.utc),
                before=before or {},
                after=after or {},
                metadata=metadata or {},
            )
        )
