import re
from typing import Iterable


class RiskAwarePhrasingService:
    def apply(self, text: str, constraints: Iterable[str], max_chars: int = 4096) -> str:
        rendered = text or ""
        normalized = {str(item).upper() for item in (constraints or [])}

        if "NO_URLS" in normalized:
            rendered = re.sub(r"https?://\S+", "[link removed]", rendered)
        if "NO_FINANCIAL_ADVICE" in normalized:
            rendered = f"{rendered}\n\nNote: this is informational, not financial advice.".strip()
        if "NO_MEDICAL_ADVICE" in normalized:
            rendered = f"{rendered}\n\nNote: this is informational, not medical advice.".strip()
        if "SAFE_TONE" in normalized and rendered:
            rendered = rendered[0].upper() + rendered[1:]

        if len(rendered) > max_chars:
            rendered = rendered[:max_chars].rstrip()
        return rendered

