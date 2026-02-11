import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List


class JwtAuthError(Exception):
    pass


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


@dataclass(frozen=True)
class JwtClaims:
    sub: str
    roles: List[str]
    raw: Dict[str, Any]


class HmacJwtVerifier:
    """
    Lightweight HS256 JWT verifier used by admin plane.
    """

    def __init__(self, secret: str, issuer: str = "", audience: str = "", leeway_seconds: int = 0):
        self.secret = secret.encode("utf-8")
        self.issuer = issuer
        self.audience = audience
        self.leeway_seconds = leeway_seconds

    def verify(self, token: str) -> JwtClaims:
        parts = token.split(".")
        if len(parts) != 3:
            raise JwtAuthError("Malformed JWT")
        header_b64, payload_b64, signature_b64 = parts

        header = json.loads(_b64url_decode(header_b64))
        if header.get("alg") != "HS256":
            raise JwtAuthError("Unsupported algorithm")

        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_sig = hmac.new(self.secret, signing_input, hashlib.sha256).digest()
        provided_sig = _b64url_decode(signature_b64)
        if not hmac.compare_digest(expected_sig, provided_sig):
            raise JwtAuthError("Invalid signature")

        payload = json.loads(_b64url_decode(payload_b64))
        now = int(datetime.now(timezone.utc).timestamp())
        exp = payload.get("exp")
        if exp is not None and now > int(exp) + self.leeway_seconds:
            raise JwtAuthError("JWT expired")
        nbf = payload.get("nbf")
        if nbf is not None and now + self.leeway_seconds < int(nbf):
            raise JwtAuthError("JWT not active yet")

        if self.issuer and payload.get("iss") != self.issuer:
            raise JwtAuthError("Invalid issuer")
        if self.audience:
            aud = payload.get("aud")
            if isinstance(aud, list):
                if self.audience not in aud:
                    raise JwtAuthError("Invalid audience")
            elif aud != self.audience:
                raise JwtAuthError("Invalid audience")

        roles = payload.get("roles") or []
        if isinstance(roles, str):
            roles = [roles]
        return JwtClaims(
            sub=str(payload.get("sub", "unknown")),
            roles=[str(x) for x in roles],
            raw=payload,
        )

    def issue_for_tests(self, claims: Dict[str, Any]) -> str:
        """
        Test helper used by unit tests.
        """
        header = {"alg": "HS256", "typ": "JWT"}
        header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        payload_b64 = _b64url_encode(json.dumps(claims, separators=(",", ":")).encode("utf-8"))
        signature = hmac.new(
            self.secret,
            f"{header_b64}.{payload_b64}".encode("ascii"),
            hashlib.sha256,
        ).digest()
        sig_b64 = _b64url_encode(signature)
        return f"{header_b64}.{payload_b64}.{sig_b64}"


ROLE_RANK = {"viewer": 1, "operator": 2, "admin": 3}


def require_role(claims: JwtClaims, required_role: str) -> None:
    if required_role not in ROLE_RANK:
        raise JwtAuthError(f"Unknown role: {required_role}")
    max_rank = 0
    for role in claims.roles:
        max_rank = max(max_rank, ROLE_RANK.get(role, 0))
    if max_rank < ROLE_RANK[required_role]:
        raise JwtAuthError(f"Insufficient role: requires {required_role}")


def has_any_role(claims: JwtClaims, roles: Iterable[str]) -> bool:
    normalized = set(claims.roles)
    return any(role in normalized for role in roles)
