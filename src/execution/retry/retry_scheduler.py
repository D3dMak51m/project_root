import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 5
    base_delay_seconds: float = 2.0
    factor: float = 2.0
    max_delay_seconds: float = 300.0
    jitter_ratio: float = 0.2


class RetryScheduler:
    def __init__(self, policy: RetryPolicy = RetryPolicy()):
        self.policy = policy

    def should_retry(self, attempt_count: int) -> bool:
        return attempt_count < self.policy.max_attempts

    def next_retry_at(self, attempt_count: int, now: datetime | None = None) -> datetime:
        base = self.policy.base_delay_seconds * (self.policy.factor ** max(0, attempt_count - 1))
        capped = min(base, self.policy.max_delay_seconds)
        spread = capped * self.policy.jitter_ratio
        delay = capped + random.uniform(-spread, spread)
        current = now or datetime.now(timezone.utc)
        return current + timedelta(seconds=max(0.1, delay))
