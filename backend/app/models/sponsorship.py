import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Sponsorship(Base):
    """Chispas que un miembro gasta para patrocinar a otro de su facción.
    Lo patrocinado en una temporada decide quién es campeón en La Última Luz."""

    __tablename__ = "sponsorships"
    __table_args__ = (
        CheckConstraint("sponsor_id <> recipient_id", name="ck_sponsorship_not_self"),
        CheckConstraint("chispas >= 1", name="ck_sponsorship_chispas_positive"),
        Index("ix_sponsorships_season_recipient", "season_id", "recipient_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    season_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("seasons.id"), nullable=False)
    sponsor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    recipient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    faction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("factions.id"), nullable=False)
    chispas: Mapped[int] = mapped_column(Integer, nullable=False)
    # Lo pone la aplicación (no server_default) para que los tests puedan inyectar `now`.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
