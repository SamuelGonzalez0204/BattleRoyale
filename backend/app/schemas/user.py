import uuid
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, EmailStr, Field

from app.core.security import BCRYPT_MAX_BYTES


def _within_bcrypt_limit(password: str) -> str:
    if len(password.encode("utf-8")) > BCRYPT_MAX_BYTES:
        raise ValueError(
            f"La contraseña no puede ocupar más de {BCRYPT_MAX_BYTES} bytes "
            "(las tildes, la ñ y los emojis cuentan como 2-4 bytes)"
        )
    return password


NewPassword = Annotated[str, Field(min_length=8), AfterValidator(_within_bcrypt_limit)]


class UserRegister(BaseModel):
    email: EmailStr
    handle: str = Field(min_length=2, max_length=60)
    password: NewPassword


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    handle: str
    faction_slug: str | None = None
    role: str | None = None
    chispas: int
    is_verified: bool
    handle_verification_status: str = "none"
    # Solo mientras está pendiente: el código que hay que poner en la bio.
    handle_verification_code: str | None = None

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    message: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=1, max_length=2048)
    new_password: NewPassword


class HandleVerificationOut(BaseModel):
    handle: str
    status: str
    code: str
    requested_at: datetime
    instructions: str
