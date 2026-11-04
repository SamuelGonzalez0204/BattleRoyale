"""Identidad: tokens de verificación/reset ligados al usuario y verificación de handle."""

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    EMAIL_VERIFICATION,
    PASSWORD_RESET,
    create_purpose_token,
    decode_purpose_token,
    hash_password,
    password_fingerprint,
)
from app.models.user import HandleVerificationStatus, User

# Sin 0/O/1/I para que el código se copie a mano sin errores.
HANDLE_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
HANDLE_CODE_LENGTH = 6
HANDLE_CODE_PREFIX = "CICLO-"


class HandleAlreadyVerified(Exception):
    pass


def issue_verification_token(user: User) -> str:
    settings = get_settings()
    return create_purpose_token(
        str(user.id),
        EMAIL_VERIFICATION,
        timedelta(hours=settings.email_verification_expire_hours),
        {"email": user.email},
    )


def issue_password_reset_token(user: User) -> str:
    settings = get_settings()
    return create_purpose_token(
        str(user.id),
        PASSWORD_RESET,
        timedelta(minutes=settings.password_reset_expire_minutes),
        {"pwd": password_fingerprint(user.hashed_password)},
    )


def _user_for_claims(db: Session, claims: dict | None) -> User | None:
    if claims is None:
        return None
    try:
        return db.get(User, uuid.UUID(claims["sub"]))
    except ValueError:
        return None


def verify_email(db: Session, token: str) -> User | None:
    """Marca el email como verificado. None si el token no vale (caducado, otro email…)."""
    claims = decode_purpose_token(token, EMAIL_VERIFICATION)
    user = _user_for_claims(db, claims)
    if user is None or claims.get("email") != user.email:
        return None
    user.is_verified = True
    return user


def reset_password(db: Session, token: str, new_password: str) -> User | None:
    """Cambia la contraseña. El token deja de valer en cuanto cambia el hash (un solo uso)."""
    claims = decode_purpose_token(token, PASSWORD_RESET)
    user = _user_for_claims(db, claims)
    if user is None or claims.get("pwd") != password_fingerprint(user.hashed_password):
        return None
    user.hashed_password = hash_password(new_password)
    return user


def generate_handle_code() -> str:
    suffix = "".join(secrets.choice(HANDLE_CODE_ALPHABET) for _ in range(HANDLE_CODE_LENGTH))
    return f"{HANDLE_CODE_PREFIX}{suffix}"


def request_handle_verification(user: User, now: datetime | None = None) -> User:
    """Genera (o rota) el código que el usuario debe poner en su bio y deja la solicitud pendiente."""
    if user.handle_verification_status == HandleVerificationStatus.verified:
        raise HandleAlreadyVerified
    user.handle_verification_code = generate_handle_code()
    user.handle_verification_status = HandleVerificationStatus.pending
    user.handle_verification_requested_at = now or datetime.now(timezone.utc)
    user.handle_verification_reviewed_at = None
    return user
