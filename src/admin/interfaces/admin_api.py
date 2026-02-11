from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from src.admin.security.jwt_hmac import HmacJwtVerifier, JwtAuthError, require_role
from src.admin.services.control_plane_service import AdminControlPlaneService
from src.core.domain.execution_intent import ExecutionIntent
from src.core.domain.resource import ResourceCost
from src.execution.domain.execution_job import DlqState

try:
    from fastapi import APIRouter, Depends, Header, HTTPException
except Exception:  # pragma: no cover - optional dependency
    APIRouter = None
    Depends = None
    Header = None
    HTTPException = None


def build_admin_router(
    service: AdminControlPlaneService,
    verifier: HmacJwtVerifier,
):
    if APIRouter is None:
        raise RuntimeError("fastapi is required to build admin router")

    router = APIRouter(prefix="/admin/v1", tags=["admin"])

    def _actor_role(claims, fallback: str) -> str:
        if getattr(claims, "roles", None):
            return str(claims.roles[0])
        return fallback

    def _claims(required_role: str):
        def _dep(authorization: Optional[str] = Header(None)):
            if not authorization or not authorization.startswith("Bearer "):
                raise HTTPException(status_code=401, detail="Missing bearer token")
            token = authorization.split(" ", 1)[1].strip()
            try:
                claims = verifier.verify(token)
                require_role(claims, required_role)
                return claims
            except JwtAuthError as exc:
                raise HTTPException(status_code=403, detail=str(exc))

        return _dep

    @router.get("/contexts")
    def get_contexts(claims=Depends(_claims("viewer"))):
        return {"items": service.list_contexts()}

    @router.get("/memory/{context_domain}")
    def get_memory(context_domain: str, limit: int = 100, claims=Depends(_claims("viewer"))):
        return service.get_memory_view(context_domain=context_domain, limit=limit)

    @router.get("/budget")
    def get_budget(limit: int = 100, claims=Depends(_claims("viewer"))):
        return service.get_budget_view(limit=limit)

    @router.get("/dlq")
    def get_dlq(limit: int = 100, claims=Depends(_claims("viewer"))):
        return {"items": service.list_dlq(limit=limit)}

    @router.post("/dlq/{job_id}/replay")
    def replay_dlq(job_id: UUID, claims=Depends(_claims("operator"))):
        replay = service.replay_dlq(job_id, actor=claims.sub, role=_actor_role(claims, "operator"))
        if not replay:
            raise HTTPException(status_code=404, detail="DLQ job not found")
        return replay

    @router.post("/dlq/{job_id}/resolve")
    def resolve_dlq(job_id: UUID, payload: Dict[str, Any], claims=Depends(_claims("operator"))):
        raw_state = str(payload.get("state", "resolved")).strip().lower()
        try:
            target = DlqState(raw_state)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid DLQ state")
        ok = service.resolve_dlq(job_id, target_state=target, actor=claims.sub, role=_actor_role(claims, "operator"))
        if not ok:
            raise HTTPException(status_code=404, detail="DLQ job not found")
        return {"status": "ok", "job_id": str(job_id), "state": target.value}

    @router.post("/control/pause")
    def set_pause(payload: Dict[str, Any], claims=Depends(_claims("admin"))):
        paused = bool(payload.get("paused", True))
        service.set_global_pause(paused=paused, actor=claims.sub, role=_actor_role(claims, "admin"))
        return {"status": "ok", "paused": paused}

    @router.post("/control/panic")
    def set_panic(payload: Dict[str, Any], claims=Depends(_claims("admin"))):
        enabled = bool(payload.get("enabled", True))
        service.set_panic_mode(enabled=enabled, actor=claims.sub, role=_actor_role(claims, "admin"))
        return {"status": "ok", "panic_mode": enabled}

    @router.post("/control/context/{context_domain}")
    def set_context(context_domain: str, payload: Dict[str, Any], claims=Depends(_claims("admin"))):
        enabled = bool(payload.get("enabled", True))
        ok = service.set_context_enabled(
            context_domain=context_domain,
            enabled=enabled,
            actor=claims.sub,
            role=_actor_role(claims, "admin"),
        )
        if not ok:
            raise HTTPException(status_code=404, detail="Context not found")
        return {"status": "ok", "context_domain": context_domain, "enabled": enabled}

    @router.post("/control/platform/{platform}")
    def set_platform(platform: str, payload: Dict[str, Any], claims=Depends(_claims("admin"))):
        enabled = bool(payload.get("enabled", True))
        service.set_platform_enabled(
            platform=platform,
            enabled=enabled,
            actor=claims.sub,
            role=_actor_role(claims, "admin"),
        )
        return {"status": "ok", "platform": platform, "enabled": enabled}

    @router.post("/intent/inject")
    def inject_intent(payload: Dict[str, Any], claims=Depends(_claims("operator"))):
        context_domain = str(payload["context_domain"])
        constraints = dict(payload.get("constraints", {}))
        intent = ExecutionIntent(
            id=UUID(payload.get("intent_id")) if payload.get("intent_id") else uuid4(),
            commitment_id=UUID(payload.get("commitment_id")) if payload.get("commitment_id") else uuid4(),
            intention_id=UUID(payload.get("intention_id")) if payload.get("intention_id") else uuid4(),
            persona_id=UUID(payload.get("persona_id")) if payload.get("persona_id") else uuid4(),
            abstract_action=str(payload.get("abstract_action", "manual_inject")),
            constraints=constraints,
            created_at=datetime.now(timezone.utc),
            reversible=bool(payload.get("reversible", False)),
            risk_level=float(payload.get("risk_level", 0.0)),
            estimated_cost=ResourceCost(
                energy_cost=float(payload.get("energy_cost", 0.0)),
                attention_cost=float(payload.get("attention_cost", 0.0)),
                execution_slot_cost=int(payload.get("execution_slot_cost", 1)),
            ),
        )
        job_id = service.inject_intent(
            intent=intent,
            context_domain=context_domain,
            actor=claims.sub,
            role=_actor_role(claims, "operator"),
        )
        return {"status": "queued", "job_id": str(job_id), "intent_id": str(intent.id)}

    return router
