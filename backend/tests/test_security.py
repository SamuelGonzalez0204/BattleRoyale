"""Unitarios de app.core.security: bcrypt directo y tokens firmados con propósito."""

from datetime import timedelta

from app.core.security import (
    EMAIL_VERIFICATION,
    PASSWORD_RESET,
    create_access_token,
    create_purpose_token,
    decode_access_token,
    decode_purpose_token,
    hash_password,
    password_fingerprint,
    verify_password,
)

# Hash generado con passlib 1.7.4 (CryptContext bcrypt) antes de retirarlo: los
# usuarios existentes deben poder seguir entrando.
LEGACY_PASSLIB_HASH = "$2b$12$OMfv0eJEGockZe7RfBJv7uxeoPaNsPMrH6YjtcrLKzsLy8Qa1M7r."
LEGACY_PASSWORD = "legacy-password-123"


def test_hash_password_roundtrip() -> None:
    hashed = hash_password("una-contraseña-larga")

    assert hashed.startswith("$2b$")
    assert verify_password("una-contraseña-larga", hashed)
    assert not verify_password("otra-contraseña", hashed)


def test_legacy_passlib_hash_still_verifies() -> None:
    assert verify_password(LEGACY_PASSWORD, LEGACY_PASSLIB_HASH)
    assert not verify_password("legacy-password-124", LEGACY_PASSLIB_HASH)


def test_verify_password_with_malformed_hash_returns_false() -> None:
    assert verify_password("lo-que-sea", "x") is False


def test_purpose_token_roundtrip_returns_claims() -> None:
    token = create_purpose_token("user-1", EMAIL_VERIFICATION, timedelta(hours=1), {"email": "a@b.c"})

    claims = decode_purpose_token(token, EMAIL_VERIFICATION)

    assert claims is not None
    assert claims["sub"] == "user-1"
    assert claims["email"] == "a@b.c"


def test_purpose_token_with_wrong_purpose_is_rejected() -> None:
    token = create_purpose_token("user-1", EMAIL_VERIFICATION, timedelta(hours=1))

    assert decode_purpose_token(token, PASSWORD_RESET) is None


def test_expired_purpose_token_is_rejected() -> None:
    token = create_purpose_token("user-1", PASSWORD_RESET, timedelta(seconds=-1))

    assert decode_purpose_token(token, PASSWORD_RESET) is None


def test_garbage_token_is_rejected() -> None:
    assert decode_purpose_token("no-es-un-jwt", PASSWORD_RESET) is None


def test_purpose_token_cannot_be_used_as_access_token() -> None:
    token = create_purpose_token("user-1", EMAIL_VERIFICATION, timedelta(hours=1))

    assert decode_access_token(token) is None


def test_access_token_cannot_be_used_as_purpose_token() -> None:
    token = create_access_token("user-1")

    assert decode_access_token(token) == "user-1"
    assert decode_purpose_token(token, EMAIL_VERIFICATION) is None


def test_password_fingerprint_changes_with_hash_and_hides_it() -> None:
    first = password_fingerprint(hash_password("primera-clave"))
    second = password_fingerprint(hash_password("primera-clave"))

    assert first != second  # sal distinta => huella distinta
    assert "$2b$" not in first
    assert len(first) == 16
