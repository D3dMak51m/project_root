import json
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Sequence, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.content.interfaces.llm_provider import LlmProvider
from src.content.providers.mock_provider import MockLlmProvider
from src.content.services.conversation_compressor import ConversationCompressor
from src.content.services.multi_provider_router import MultiProviderRouter
from src.content.services.prompt_injection_filter import PromptInjectionFilter, PromptInjectionVerdict
from src.content.services.prompt_template_registry import PromptTemplateRegistry
from src.content.services.risk_aware_phrasing_service import RiskAwarePhrasingService
from src.core.domain.execution_intent import ExecutionIntent


@dataclass(frozen=True)
class ContentGenerationOutcome:
    text: str
    provider: str
    model: str
    fallback_used: bool
    decision: str
    error: str = ""


class ContentGenerationService:
    def __init__(
        self,
        template_registry: PromptTemplateRegistry,
        provider_router: MultiProviderRouter,
        compressor: Optional[ConversationCompressor] = None,
        injection_filter: Optional[PromptInjectionFilter] = None,
        risk_aware_phrasing: Optional[RiskAwarePhrasingService] = None,
        engine: Optional[Engine] = None,
    ):
        self.template_registry = template_registry
        self.provider_router = provider_router
        self.compressor = compressor or ConversationCompressor()
        self.injection_filter = injection_filter or PromptInjectionFilter()
        self.risk_aware_phrasing = risk_aware_phrasing or RiskAwarePhrasingService()
        self.engine = engine
        if self.engine:
            self.ensure_schema()

    @classmethod
    def from_providers(
        cls,
        providers: Sequence[LlmProvider],
        dsn: Optional[str] = None,
    ) -> "ContentGenerationService":
        engine = create_engine(dsn, pool_pre_ping=True, future=True) if dsn else None
        registry = PromptTemplateRegistry(engine=engine)
        router = MultiProviderRouter(providers=list(providers))
        return cls(
            template_registry=registry,
            provider_router=router,
            compressor=ConversationCompressor(),
            injection_filter=PromptInjectionFilter(),
            risk_aware_phrasing=RiskAwarePhrasingService(),
            engine=engine,
        )

    @classmethod
    def with_mock(cls) -> "ContentGenerationService":
        return cls.from_providers([MockLlmProvider()])

    def ensure_schema(self) -> None:
        if not self.engine:
            return
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS content_generation_events (
                        intent_id UUID NOT NULL,
                        provider TEXT NOT NULL,
                        model TEXT NOT NULL,
                        latency_ms DOUBLE PRECISION NOT NULL,
                        fallback_used BOOLEAN NOT NULL DEFAULT FALSE,
                        decision TEXT NOT NULL,
                        error TEXT NOT NULL DEFAULT '',
                        created_at TIMESTAMPTZ NOT NULL,
                        metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS ix_content_generation_events_created
                    ON content_generation_events (created_at DESC)
                    """
                )
            )

    def apply_to_intent(
        self,
        intent: ExecutionIntent,
        trace_id: Optional[str] = None,
    ) -> Tuple[ExecutionIntent, ContentGenerationOutcome]:
        constraints = dict(intent.constraints)
        if not constraints.get("content_generation_required"):
            text = str(constraints.get("text", ""))
            return intent, ContentGenerationOutcome(
                text=text,
                provider="disabled",
                model=str(constraints.get("llm_model", "n/a")),
                fallback_used=False,
                decision="skip",
            )

        now = datetime.now(timezone.utc)
        started = time.monotonic()
        user_message = str(constraints.get("user_message", constraints.get("text", "")))
        conversation_history = constraints.get("conversation_history", [])
        if not isinstance(conversation_history, list):
            conversation_history = []
        verdict = self.injection_filter.evaluate(user_message)

        model = str(constraints.get("llm_model", "gpt-4o-mini"))
        max_tokens = int(constraints.get("llm_max_tokens", 256))
        temperature = float(constraints.get("llm_temperature", 0.2))
        policy_constraints = constraints.get("policy_constraints", [])
        if not isinstance(policy_constraints, list):
            policy_constraints = []

        if verdict.decision == "block":
            fallback_text = self._fallback_text(constraints, verdict)
            final_text = self.risk_aware_phrasing.apply(fallback_text, policy_constraints)
            outcome = ContentGenerationOutcome(
                text=final_text,
                provider="fallback",
                model=model,
                fallback_used=True,
                decision=verdict.decision,
                error=verdict.reason,
            )
            updated = self._apply_outcome(intent, outcome)
            self._record_event(intent.id, outcome, (time.monotonic() - started) * 1000.0, now)
            return updated, outcome

        conversation_summary = self.compressor.compress(
            [str(x) for x in conversation_history],
            token_budget=int(constraints.get("context_token_budget", 512)),
        )
        template_id = str(constraints.get("prompt_template_id", "telegram_default"))
        try:
            prompt = self.template_registry.render(
                template_id=template_id,
                variables={
                    "context_domain": str(constraints.get("context_domain", "")),
                    "user_message": verdict.sanitized_text,
                    "conversation_summary": conversation_summary,
                    "intent_id": str(intent.id),
                },
            )
        except Exception:
            prompt = (
                "Context domain: {context_domain}\n"
                "User message: {user_message}\n"
                "Conversation summary: {conversation_summary}\n"
                "Respond with a concise, safe answer."
            ).format(
                context_domain=str(constraints.get("context_domain", "")),
                user_message=verdict.sanitized_text,
                conversation_summary=conversation_summary,
            )

        try:
            generated, provider_trace = self.provider_router.generate(
                prompt=prompt,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                trace_id=trace_id or str(intent.id),
            )
            raw_text = generated.text.strip() or self._fallback_text(constraints, verdict)
            final_text = self.risk_aware_phrasing.apply(raw_text, policy_constraints)
            error = ""
            if provider_trace.attempts and not provider_trace.attempts[-1].ok:
                error = provider_trace.attempts[-1].error
            outcome = ContentGenerationOutcome(
                text=final_text,
                provider=generated.provider,
                model=generated.model,
                fallback_used=False,
                decision=verdict.decision,
                error=error,
            )
        except Exception as exc:
            fallback_text = self._fallback_text(constraints, verdict)
            final_text = self.risk_aware_phrasing.apply(fallback_text, policy_constraints)
            outcome = ContentGenerationOutcome(
                text=final_text,
                provider="fallback",
                model=model,
                fallback_used=True,
                decision=verdict.decision,
                error=str(exc),
            )

        updated_intent = self._apply_outcome(intent, outcome)
        self._record_event(intent.id, outcome, (time.monotonic() - started) * 1000.0, now)
        return updated_intent, outcome

    def _fallback_text(self, constraints: Dict[str, Any], verdict: PromptInjectionVerdict) -> str:
        template = str(
            constraints.get(
                "fallback_template",
                "I received your message. Please rephrase and I will respond safely.",
            )
        )
        if verdict.decision == "sanitize":
            return f"{template}\n\n[Input sanitized for safety.]"
        if verdict.decision == "block":
            return "I cannot process that request safely. Please send a different message."
        return template

    def _apply_outcome(self, intent: ExecutionIntent, outcome: ContentGenerationOutcome) -> ExecutionIntent:
        merged = dict(intent.constraints)
        merged["text"] = outcome.text
        merged["content_generation_meta"] = {
            "provider": outcome.provider,
            "model": outcome.model,
            "fallback_used": outcome.fallback_used,
            "decision": outcome.decision,
            "error": outcome.error,
        }
        return replace(intent, constraints=merged)

    def _record_event(
        self,
        intent_id,
        outcome: ContentGenerationOutcome,
        latency_ms: float,
        created_at: datetime,
    ) -> None:
        if not self.engine:
            return
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO content_generation_events (
                        intent_id, provider, model, latency_ms, fallback_used,
                        decision, error, created_at, metadata_json
                    ) VALUES (
                        :intent_id, :provider, :model, :latency_ms, :fallback_used,
                        :decision, :error, :created_at, :metadata_json::jsonb
                    )
                    """
                ),
                {
                    "intent_id": intent_id,
                    "provider": outcome.provider,
                    "model": outcome.model,
                    "latency_ms": float(latency_ms),
                    "fallback_used": bool(outcome.fallback_used),
                    "decision": outcome.decision,
                    "error": outcome.error,
                    "created_at": created_at,
                    "metadata_json": json.dumps({"decision": outcome.decision}),
                },
            )

