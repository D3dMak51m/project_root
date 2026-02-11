from datetime import datetime, timedelta, timezone

import pytest

from src.admin.security.jwt_hmac import HmacJwtVerifier, JwtAuthError, require_role


def test_jwt_hmac_verifier_accepts_valid_token_and_roles():
    verifier = HmacJwtVerifier(secret="test-secret", issuer="ops")
    token = verifier.issue_for_tests(
        {
            "sub": "alice",
            "roles": ["operator"],
            "iss": "ops",
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp()),
        }
    )

    claims = verifier.verify(token)
    assert claims.sub == "alice"
    assert "operator" in claims.roles
    require_role(claims, "viewer")


def test_jwt_hmac_verifier_rejects_bad_signature():
    verifier = HmacJwtVerifier(secret="test-secret")
    token = verifier.issue_for_tests(
        {
            "sub": "alice",
            "roles": ["admin"],
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp()),
        }
    )
    tampered = token[:-1] + ("a" if token[-1] != "a" else "b")

    with pytest.raises(JwtAuthError):
        verifier.verify(tampered)


def test_require_role_blocks_insufficient_role():
    verifier = HmacJwtVerifier(secret="test-secret")
    token = verifier.issue_for_tests(
        {
            "sub": "bob",
            "roles": ["viewer"],
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp()),
        }
    )
    claims = verifier.verify(token)

    with pytest.raises(JwtAuthError):
        require_role(claims, "operator")
