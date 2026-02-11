import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from string import Template
from threading import Lock
from typing import Any, Dict, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


@dataclass(frozen=True)
class PromptTemplate:
    template_id: str
    version: int
    body: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    active: bool = True


class PromptTemplateRegistry:
    def __init__(self, engine: Optional[Engine] = None):
        self.engine = engine
        self._cache: Dict[str, PromptTemplate] = {}
        self._lock = Lock()
        if self.engine:
            self.ensure_schema()
        self._seed_defaults()

    @classmethod
    def from_dsn(cls, dsn: str) -> "PromptTemplateRegistry":
        engine = create_engine(dsn, pool_pre_ping=True, future=True)
        return cls(engine=engine)

    def ensure_schema(self) -> None:
        if not self.engine:
            return
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS prompt_templates (
                        template_id TEXT NOT NULL,
                        version INTEGER NOT NULL,
                        body TEXT NOT NULL,
                        metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                        active BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMPTZ NOT NULL,
                        PRIMARY KEY (template_id, version)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS ix_prompt_templates_active
                    ON prompt_templates (template_id, active, version DESC)
                    """
                )
            )

    def upsert_template(
        self,
        template_id: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None,
        active: bool = True,
        version: Optional[int] = None,
    ) -> PromptTemplate:
        with self._lock:
            current = self.get_template(template_id)
            next_version = version if version is not None else ((current.version + 1) if current else 1)
            template = PromptTemplate(
                template_id=template_id,
                version=next_version,
                body=body,
                metadata=dict(metadata or {}),
                active=active,
            )
            self._cache[template_id] = template

        if self.engine:
            now = datetime.now(timezone.utc)
            with self.engine.begin() as conn:
                if active:
                    conn.execute(
                        text(
                            """
                            UPDATE prompt_templates
                            SET active=FALSE
                            WHERE template_id=:template_id
                            """
                        ),
                        {"template_id": template_id},
                    )
                conn.execute(
                    text(
                        """
                        INSERT INTO prompt_templates (
                            template_id, version, body, metadata_json, active, created_at
                        ) VALUES (
                            :template_id, :version, :body, :metadata_json::jsonb, :active, :created_at
                        )
                        ON CONFLICT (template_id, version)
                        DO UPDATE SET
                            body=EXCLUDED.body,
                            metadata_json=EXCLUDED.metadata_json,
                            active=EXCLUDED.active
                        """
                    ),
                    {
                        "template_id": template_id,
                        "version": next_version,
                        "body": body,
                        "metadata_json": json.dumps(metadata or {}),
                        "active": active,
                        "created_at": now,
                    },
                )
        return template

    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        cached = self._cache.get(template_id)
        if cached:
            return cached
        if not self.engine:
            return None
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT template_id, version, body, metadata_json, active
                    FROM prompt_templates
                    WHERE template_id=:template_id AND active=TRUE
                    ORDER BY version DESC
                    LIMIT 1
                    """
                ),
                {"template_id": template_id},
            ).first()
            if not row:
                return None
            template = PromptTemplate(
                template_id=row.template_id,
                version=int(row.version),
                body=row.body,
                metadata=dict(row.metadata_json or {}),
                active=bool(row.active),
            )
            with self._lock:
                self._cache[template_id] = template
            return template

    def render(self, template_id: str, variables: Dict[str, Any]) -> str:
        template = self.get_template(template_id)
        if not template:
            raise KeyError(f"Template not found: {template_id}")
        safe_vars = {k: str(v) for k, v in variables.items()}
        return Template(template.body).safe_substitute(safe_vars)

    def _seed_defaults(self) -> None:
        if self.get_template("telegram_default"):
            return
        self.upsert_template(
            template_id="telegram_default",
            body=(
                "System: You are a strategic assistant in Telegram.\n"
                "Context domain: ${context_domain}\n"
                "User message: ${user_message}\n"
                "Conversation summary: ${conversation_summary}\n"
                "Produce a concise, safe reply."
            ),
            metadata={"kind": "telegram"},
            active=True,
            version=1,
        )

