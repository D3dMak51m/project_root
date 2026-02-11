import hashlib
import hmac


class TelegramWebhookSecurityService:
    def __init__(self, secret_token: str):
        self.secret_token = secret_token or ""

    def verify_token(self, candidate: str) -> bool:
        return hmac.compare_digest(self.secret_token.encode("utf-8"), (candidate or "").encode("utf-8"))

    def payload_hash(self, payload: bytes) -> str:
        return hashlib.sha256(payload).hexdigest()

