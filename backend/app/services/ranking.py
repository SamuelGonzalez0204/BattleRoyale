"""Ranking (Fase E2): Chispas actuales o votos emitidos en la temporada activa.

Rango con RANK(): empates comparten puesto (1, 1, 3) y se listan por handle.
Tres consultas fijas (página, total, mi puesto), sin N+1.
"""

import enum
import uuid
from dataclasses import dataclass

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.orm import Session

from app.models.decision import Decision, Vote
from app.models.faction import Faction
from app.models.season import Season
from app.models.user import User


class RankingScope(str, enum.Enum):
    chispas = "chispas"
    votos = "votos"


class UnknownFaction(Exception):
    pass


@dataclass(frozen=True)
class RankingRow:
    rank: int
    user_id: uuid.UUID
    handle: str
    faction_slug: str | None
    role: str | None
    value: int


@dataclass(frozen=True)
class MyRank:
    rank: int
    value: int


@dataclass(frozen=True)
class RankingPage:
    items: list[RankingRow]
    total: int
    me: MyRank | None


def _season_votes(season: Season):
    return (
        select(Vote.user_id, func.count(Vote.id).label("votes"))
        .join(Decision, Decision.id == Vote.decision_id)
        .where(Decision.season_id == season.id)
        .group_by(Vote.user_id)
        .subquery()
    )


def _ranked(scope: RankingScope, season: Season | None, faction_id: uuid.UUID | None):
    query: Select
    value: ColumnElement[int]
    if scope == RankingScope.votos:
        if season is None:
            raise ValueError("No hay una temporada activa configurada")
        votes = _season_votes(season)
        value = func.coalesce(votes.c.votes, 0)
        query = select(User.id).outerjoin(votes, votes.c.user_id == User.id)
    else:
        value = User.chispas
        query = select(User.id)
    query = query.outerjoin(Faction, Faction.id == User.faction_id).add_columns(
        User.handle,
        Faction.slug.label("faction_slug"),
        User.role,
        value.label("value"),
        func.rank().over(order_by=value.desc()).label("rank"),
    )
    if faction_id is not None:
        query = query.where(User.faction_id == faction_id)
    return query.subquery()


def _faction_id(db: Session, slug: str | None) -> uuid.UUID | None:
    if slug is None:
        return None
    faction_id = db.query(Faction.id).filter(Faction.slug == slug).scalar()
    if faction_id is None:
        raise UnknownFaction("Esa facción no existe")
    return faction_id


def ranking_page(
    db: Session,
    *,
    scope: RankingScope,
    season: Season | None,
    faction_slug: str | None,
    limit: int,
    offset: int,
    me_id: uuid.UUID,
) -> RankingPage:
    ranked = _ranked(scope, season, _faction_id(db, faction_slug))
    rows = db.execute(
        select(ranked).order_by(ranked.c.value.desc(), ranked.c.handle.asc()).limit(limit).offset(offset)
    ).all()
    total = db.execute(select(func.count()).select_from(ranked)).scalar_one()
    mine = db.execute(select(ranked.c.rank, ranked.c.value).where(ranked.c.id == me_id)).first()
    items = [
        RankingRow(
            rank=int(row.rank),
            user_id=row.id,
            handle=row.handle,
            faction_slug=row.faction_slug,
            role=row.role.value if row.role else None,
            value=int(row.value),
        )
        for row in rows
    ]
    me = MyRank(rank=int(mine.rank), value=int(mine.value)) if mine else None
    return RankingPage(items=items, total=int(total), me=me)
