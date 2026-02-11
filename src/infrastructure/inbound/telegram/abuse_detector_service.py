from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Deque, Dict, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.interaction.domain.interaction_event import InteractionEvent


@dataclass(frozen=True)
class AbuseDecision:
    throttled: bool
    reason: str = ""


class AbuseDetectorService:
    """
    Soft-throttle detector for per-user/per-chat inbound bursts.
    """

    def __init__(
        self,
        per_user_limit: int = 20,
        per_chat_limit: int = 100,
        window_seconds: int = 60,
        engine: Optional[Engine] = None,
    ):
        self.per_user_limit = max(1, int(per_user_limit))
        self.per_chat_limit = max(1, int(per_chat_limit))
        self.window_seconds = max(10, int(window_seconds))
        self.engine = engine
        self._user_events: Dict[str, Deque[datetime]] = {}
        self._chat_events: Dict[str, Deque[datetime]] = {}
        self._lock = Lock()
        if self.engine:
            self.ensure_schema()

    @classmethod
    def from_dsn(
        cls,
        dsn: str,
        per_user_limit: int = 20,
        per_chat_limit: int = 100,
        window_seconds: int = 60,
    ) -> "AbuseDetectorService":
        engine = create_engine(dsn, pool_pre_ping=True, future=True)
        return cls(
            per_user_limit=per_user_limit,
            per_chat_limit=per_chat_limit,
            window_seconds=window_seconds,
            engine=engine,
        )

    def ensure_schema(self) -> None:
        assert self.engine is not None
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS telegram_abuse_snapshots (
                        observed_at TIMESTAMPTZ NOT NULL,
                        chat_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        user_count INTEGER NOT NULL,
                        chat_count INTEGER NOT NULL
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS ix_telegram_abuse_snapshots_observed
                    ON telegram_abuse_snapshots (observed_at DESC)
                    """
                )
            )

    def evaluate(self, event: InteractionEvent) -> AbuseDecision:
        if event.message_type == "command":
            return AbuseDecision(throttled=False, reason="command_bypass")
        now = datetime.now(timezone.utc)
        user_key = f"{event.platform}:{event.user_id}"
        chat_key = f"{event.platform}:{event.chat_id}"
        with self._lock:
            user_window = self._user_events.setdefault(user_key, deque())
            chat_window = self._chat_events.setdefault(chat_key, deque())
            self._trim(user_window, now)
            self._trim(chat_window, now)
            user_window.append(now)
            chat_window.append(now)
            user_count = len(user_window)
            chat_count = len(chat_window)
        if self.engine:
            self._snapshot(event.chat_id, event.user_id, user_count, chat_count, now)
        if user_count > self.per_user_limit:
            return AbuseDecision(True, "per_user_threshold")
        if chat_count > self.per_chat_limit:
            return AbuseDecision(True, "per_chat_threshold")
        return AbuseDecision(False, "")

    def _trim(self, values: Deque[datetime], now: datetime) -> None:
        cutoff = now - timedelta(seconds=self.window_seconds)
        while values and values[0] < cutoff:
            values.popleft()

    def _snapshot(self, chat_id: str, user_id: str, user_count: int, chat_count: int, observed_at: datetime) -> None:
        assert self.engine is not None
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO telegram_abuse_snapshots (
                        observed_at, chat_id, user_id, user_count, chat_count
                    ) VALUES (
                        :observed_at, :chat_id, :user_id, :user_count, :chat_count
                    )
                    """
                ),
                {
                    "observed_at": observed_at,
                    "chat_id": chat_id,
                    "user_id": user_id,
                    "user_count": int(user_count),
                    "chat_count": int(chat_count),
                },
            )

