from typing import Iterable, List, Optional


class ConversationCompressor:
    """
    Deterministic token-bound compressor with recency + salience bias.
    """

    def __init__(self, default_token_budget: int = 512):
        self.default_token_budget = max(64, int(default_token_budget))

    def compress(self, messages: Iterable[str], token_budget: Optional[int] = None) -> str:
        budget = max(16, int(token_budget or self.default_token_budget))
        normalized = [self._normalize(x) for x in messages if self._normalize(x)]
        if not normalized:
            return ""

        scored = list(enumerate(normalized))
        scored.sort(key=lambda item: (self._salience(item[1]), item[0]))

        chosen: List[str] = []
        tokens_used = 0
        # Always keep the most recent items if possible.
        recent = normalized[-4:]
        for text in recent:
            estimated = self._estimate_tokens(text)
            if tokens_used + estimated > budget:
                break
            chosen.append(text)
            tokens_used += estimated

        # Fill with high-salience older items.
        for idx, text in reversed(scored):
            if text in chosen:
                continue
            estimated = self._estimate_tokens(text)
            if tokens_used + estimated > budget:
                continue
            chosen.append(text)
            tokens_used += estimated
            if tokens_used >= budget:
                break

        return "\n".join(chosen)

    def _normalize(self, text: str) -> str:
        return " ".join((text or "").split())

    def _estimate_tokens(self, text: str) -> int:
        # Cheap approximation for production-safe deterministic bounds.
        return max(1, int(len(text.split()) * 1.3))

    def _salience(self, text: str) -> int:
        score = 0
        lowered = text.lower()
        if "?" in text:
            score += 3
        if "!" in text:
            score += 1
        if "/help" in lowered or "/start" in lowered:
            score += 4
        if "risk" in lowered or "policy" in lowered:
            score += 2
        return score
