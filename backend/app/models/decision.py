import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Decision(Base):
    """La decisión diaria que la web abre, independiente del calendario de vídeos."""

    __tablename__ = "decisions"
    __table_args__ = (UniqueConstraint("season_id", "day", name="uq_decision_season_day"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    season_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("seasons.id"))
    day: Mapped[date] = mapped_column(Date, nullable=False)

    question: Mapped[str] = mapped_column(String(280), nullable=False)
    option_a: Mapped[str] = mapped_column(String(120), nullable=False)
    option_b: Mapped[str] = mapped_column(String(120), nullable=False)
    closes_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Vote(Base):
    """Un voto por usuario y decisión; el peso extra sale de gastar Chispas."""

    __tablename__ = "votes"
    __table_args__ = (UniqueConstraint("decision_id", "user_id", name="uq_vote_decision_user"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    decision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("decisions.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    option: Mapped[str] = mapped_column(String(1), nullable=False)  # "a" | "b"
    weight: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
