import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

# bcrypt solo usa los primeros 72 bytes; los schemas rechazan contraseñas más largas.
BCRYPT_MAX_BYTES = 72

# Propósitos de los tokens enviados por email. Un token con `purpose` nunca vale como sesión.
EMAIL_VERIFICATION = "email_verification"
PASSWORD_RESET = "password_reset"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compatible con los hashes $2b$ que generaba passlib (mismo formato modular crypt)."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("ascii"))
    except (ValueError, UnicodeEncodeError):
        # Hash corrupto o con formato desconocido: se trata como contraseña incorrecta.
        return False


def password_fingerprint(hashed_password: str) -> str:
    """Huella corta del hash actual: ata un token de reset a la contraseña vigente,
    así deja de valer en cuanto la contraseña cambia (token de un solo uso)."""
    return hashlib.sha256(hashed_password.encode("utf-8")).hexdigest()[:16]


def _encode(payload: dict[str, Any]) -> str:
    settings = get_settings()
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _decode(token: str) -> dict[str, Any] | None:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


def create_access_token(subject: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return _encode({"sub": subject, "exp": expire})


def decode_access_token(token: str) -> str | None:
    payload = _decode(token)
    if payload is None or "purpose" in payload:
        return None
    return payload.get("sub")


def create_purpose_token(
    subject: str,
    purpose: str,
    expires_in: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    expire = datetime.now(timezone.utc) + expires_in
    return _encode({**(extra_claims or {}), "sub": subject, "purpose": purpose, "exp": expire})


def decode_purpose_token(token: str, purpose: str) -> dict[str, Any] | None:
    """Devuelve los claims si el token es válido, no ha caducado y es del propósito pedido."""
    payload = _decode(token)
    if payload is None or payload.get("purpose") != purpose or not payload.get("sub"):
        return None
    return payload
