import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PromptInjectionVerdict:
    decision: str  # allow | sanitize | block
    sanitized_text: str
    reason: str


class PromptInjectionFilter:
    def __init__(self):
        self._block_patterns = [
            re.compile(r"ignore\s+previous\s+instructions", re.IGNORECASE),
            re.compile(r"reveal\s+system\s+prompt", re.IGNORECASE),
            re.compile(r"print\s+api[_\s-]?key", re.IGNORECASE),
        ]
        self._sanitize_patterns = [
            re.compile(r"bypass\s+policy", re.IGNORECASE),
            re.compile(r"disable\s+safety", re.IGNORECASE),
        ]

    def evaluate(self, text: str) -> PromptInjectionVerdict:
        source = text or ""
        for pattern in self._block_patterns:
            if pattern.search(source):
                return PromptInjectionVerdict(
                    decision="block",
                    sanitized_text="",
                    reason=f"blocked:{pattern.pattern}",
                )

        sanitized = source
        triggered = False
        for pattern in self._sanitize_patterns:
            if pattern.search(sanitized):
                sanitized = pattern.sub("[sanitized]", sanitized)
                triggered = True

        if triggered:
            return PromptInjectionVerdict(
                decision="sanitize",
                sanitized_text=sanitized,
                reason="sanitize:policy_bypass_pattern",
            )
        return PromptInjectionVerdict(decision="allow", sanitized_text=source, reason="ok")

