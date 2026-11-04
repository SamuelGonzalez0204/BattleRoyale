"""Lecturas de facciones: resumen público (miembros/influencia) y miembros de la mía."""

import uuid
from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.faction import Faction
from app.models.season import Season
from app.models.sponsorship import Sponsorship
from app.models.user import User
from app.services.sorting import faction_counts


class NoFaction(Exception):
    """Quien consulta todavía no tiene facción."""


@dataclass(frozen=True)
class FactionSummary:
    id: uuid.UUID
    slug: str
    name: str
    color: str
    members: int
    influence_pct: float


@dataclass(frozen=True)
class FactionMember:
    user_id: uuid.UUID
    handle: str
    role: str | None
    sponsored_total: int


def faction_summaries(db: Session) -> list[FactionSummary]:
    """Las facciones por slug con su número de miembros y % de influencia (2 consultas)."""
    factions = db.query(Faction).order_by(Faction.slug).all()
    counts = faction_counts(db)
    total = sum(counts.values()) or 1
    return [
        FactionSummary(
            id=f.id,
            slug=f.slug,
            name=f.name,
            color=f.color,
            members=counts.get(str(f.id), 0),
            influence_pct=round(100 * counts.get(str(f.id), 0) / total, 1),
        )
        for f in factions
    ]


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def faction_members(
    db: Session, me: User, season: Season | None, prefix: str | None, limit: int
) -> list[FactionMember]:
    """Miembros de mi facción menos yo, con lo patrocinado en `season` (0 sin temporada).
    Orden: más patrocinado primero y, a igualdad, por handle. Una sola consulta."""
    if me.faction_id is None:
        raise NoFaction("Necesitas una facción para ver a sus miembros")
    season_id = season.id if season else None
    sponsored = (
        db.query(Sponsorship.recipient_id, func.sum(Sponsorship.chispas).label("total"))
        .filter(Sponsorship.season_id == season_id)
        .group_by(Sponsorship.recipient_id)
        .subquery()
    )
    total = func.coalesce(sponsored.c.total, 0)
    query = (
        db.query(User.id, User.handle, User.role, total.label("sponsored_total"))
        .outerjoin(sponsored, sponsored.c.recipient_id == User.id)
        .filter(User.faction_id == me.faction_id, User.id != me.id)
    )
    if prefix:
        query = query.filter(User.handle.ilike(f"{_escape_like(prefix)}%", escape="\\"))
    rows = query.order_by(total.desc(), User.handle.asc()).limit(limit).all()
    return [
        FactionMember(
            user_id=row.id,
            handle=row.handle,
            role=row.role.value if row.role else None,
            sponsored_total=int(row.sponsored_total),
        )
        for row in rows
    ]
