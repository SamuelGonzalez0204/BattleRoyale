"""La Última Luz: el battle royale que cierra cada temporada (Fase B).

Un `BattleRoyaleEvent` por temporada. Las zonas son las 7 regiones del mapa
(`services/battle_royale/zones.py`); las que ya han caído se guardan en orden en
`fallen_zones`. Cada facción con miembros tiene un `Champion`; cada ronda hay un
`Duel` en la zona que cae, y los miembros votan su táctica con `TacticVote`.
"""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BrEventStatus(str, enum.Enum):
    active = "active"  # rondas en curso
    finished = "finished"  # hay ganador, falta el sello
    sealed = "sealed"  # sello elegido y temporada siguiente creada


class BrTactic(str, enum.Enum):
    ataque = "ataque"
    defensa = "defensa"
    astucia = "astucia"


class BrSeal(str, enum.Enum):
    abundancia = "abundancia"
    muralla = "muralla"
    oro = "oro"
    eco = "eco"
    cuna = "cuna"


class BattleRoyaleEvent(Base):
    __tablename__ = "br_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    season_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("seasons.id"), unique=True)
    status: Mapped[BrEventStatus] = mapped_column(
        Enum(BrEventStatus, name="br_event_status"), default=BrEventStatus.active, nullable=False
    )
    round_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # Ids de región en el orden en que cayeron: ["bahia", "campos", ...]
    fallen_zones: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    winner_faction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("factions.id"), nullable=True
    )

    # Sello: lo elige el campeón ganador (o un admin) antes de seal_deadline; si no, "eco".
    seal_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    seal: Mapped[BrSeal | None] = mapped_column(Enum(BrSeal, name="br_seal"), nullable=True)
    sealed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sealed_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    next_season_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("seasons.id"), nullable=True
    )


class Champion(Base):
    __tablename__ = "br_champions"
    __table_args__ = (
        UniqueConstraint("event_id", "faction_id", name="uq_champion_event_faction"),
        CheckConstraint("wounds >= 0", name="ck_champion_wounds_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("br_events.id"), nullable=False)
    faction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("factions.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    wounds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    eliminated_round: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Duel(Base):
    __tablename__ = "br_duels"
    __table_args__ = (UniqueConstraint("event_id", "round_number", name="uq_duel_event_round"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("br_events.id"), nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    zone: Mapped[str] = mapped_column(String(32), nullable=False)
    # Día UTC en cuyo cierre de las 23:59 se resuelve el duelo.
    resolves_on: Mapped[date] = mapped_column(Date, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    wounded_champion_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("br_champions.id"), nullable=True
    )
    # Resultado revelado al resolver: {"factions": [{slug, tactic, participation, score, ...}], "wounded": slug}
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    @property
    def is_resolved(self) -> bool:
        return self.resolved_at is not None


class TacticVote(Base):
    """Un voto por usuario y duelo; peso = 1 + Chispas gastadas."""

    __tablename__ = "br_tactic_votes"
    __table_args__ = (
        UniqueConstraint("duel_id", "user_id", name="uq_tactic_vote_duel_user"),
        CheckConstraint("chispas_spent >= 0", name="ck_tactic_vote_chispas_non_negative"),
        CheckConstraint("weight >= 1", name="ck_tactic_vote_weight_positive"),
        Index("ix_br_tactic_votes_duel_faction", "duel_id", "faction_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    duel_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("br_duels.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    # Facción del votante en el momento del voto.
    faction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("factions.id"), nullable=False)
    tactic: Mapped[BrTactic] = mapped_column(Enum(BrTactic, name="br_tactic"), nullable=False)
    chispas_spent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    weight: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
