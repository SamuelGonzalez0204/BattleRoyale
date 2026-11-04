import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserRole(str, enum.Enum):
    mercader = "mercader"
    guardia = "guardia"
    cronista = "cronista"
    explorador = "explorador"


class HandleVerificationStatus(str, enum.Enum):
    none = "none"
    pending = "pending"
    verified = "verified"
    rejected = "rejected"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    handle: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    faction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("factions.id"), nullable=True
    )
    role: Mapped[UserRole | None] = mapped_column(Enum(UserRole, name="user_role"), nullable=True)
    chispas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Acceso al panel /api/admin. Se concede con `python -m app.cli make-admin <email>`.
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)

    # Verificación manual del handle de IG/TikTok (la revisión llega con el panel de admin, D4)
    handle_verification_status: Mapped[HandleVerificationStatus] = mapped_column(
        Enum(HandleVerificationStatus, name="handle_verification_status"),
        default=HandleVerificationStatus.none,
        server_default=HandleVerificationStatus.none.value,
        nullable=False,
    )
    handle_verification_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    handle_verification_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    handle_verification_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    faction: Mapped["Faction | None"] = relationship(back_populates="users")  # noqa: F821
