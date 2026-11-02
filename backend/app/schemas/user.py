import uuid

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    handle: str = Field(min_length=2, max_length=60)
    password: str = Field(min_length=8, max_length=128)


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

    model_config = {"from_attributes": True}
