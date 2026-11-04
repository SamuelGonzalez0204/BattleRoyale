import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.decision_template import REGION_CHECK
from app.models.user import UserRole


class Decision(Base):
    """La decisión diaria que la web abre, independiente del calendario de vídeos."""

    __tablename__ = "decisions"
    __table_args__ = (
        UniqueConstraint("season_id", "day", name="uq_decision_season_day"),
        CheckConstraint(f"region IS NULL OR {REGION_CHECK}", name="ck_decision_region"),
        Index("ix_decisions_template_day", "template_id", "day"),
        Index("ix_decisions_closed_day", "day", postgresql_where=text("closed_at IS NOT NULL")),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    season_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("seasons.id"))
    day: Mapped[date] = mapped_column(Date, nullable=False)

    question: Mapped[str] = mapped_column(String(280), nullable=False)
    option_a: Mapped[str] = mapped_column(String(120), nullable=False)
    option_b: Mapped[str] = mapped_column(String(120), nullable=False)
    closes_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Efectos copiados de la plantilla al crear la decisión: {"comida": 8, "oro": -5}
    effects_a: Mapped[dict[str, int]] = mapped_column(JSONB, default=dict, nullable=False)
    effects_b: Mapped[dict[str, int]] = mapped_column(JSONB, default=dict, nullable=False)
    role_affinity: Mapped[UserRole | None] = mapped_column(Enum(UserRole, name="user_role"), nullable=True)

    # Fase E: región del mapa (copiada de la plantilla) y plantilla de origen.
    # Ambas NULL en decisiones de emergencia escritas a mano por un admin.
    region: Mapped[str | None] = mapped_column(String(32), nullable=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decision_templates.id"), nullable=True
    )

    # Cierre: None mientras sigue abierta. winner es "a" | "b" | None (nadie votó).
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    winner: Mapped[str | None] = mapped_column(String(1), nullable=True)

    @property
    def is_closed(self) -> bool:
        return self.closed_at is not None


class Vote(Base):
    """Un voto por usuario y decisión; el peso extra sale de gastar Chispas."""

    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint("decision_id", "user_id", name="uq_vote_decision_user"),
        Index("ix_votes_user_decision", "user_id", "decision_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    decision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("decisions.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    option: Mapped[str] = mapped_column(String(1), nullable=False)  # "a" | "b"
    weight: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
