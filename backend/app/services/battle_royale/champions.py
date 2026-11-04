"""Elección de campeones de La Última Luz: uno por facción, al empezar el evento.

Regla: el miembro de la facción que más Chispas ha recibido por patrocinio en la
temporada (empate: el que recibió su primer patrocinio antes). Si nadie de la
facción fue patrocinado, el miembro con más Chispas en saldo (empate: la cuenta
más antigua). Último desempate siempre por handle. Sin miembros, no hay campeón.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.faction import Faction
from app.models.season import Season
from app.models.sponsorship import Sponsorship
from app.models.user import User


@dataclass(frozen=True)
class ChampionCandidate:
    user_id: uuid.UUID
    handle: str
    sponsored_chispas: int
    first_sponsored_at: datetime | None
    chispas: int
    joined_at: datetime


def _by_sponsorship(candidate: ChampionCandidate) -> tuple[int, float, str]:
    first = candidate.first_sponsored_at
    return (-candidate.sponsored_chispas, first.timestamp() if first else float("inf"), candidate.handle)


def _by_balance(candidate: ChampionCandidate) -> tuple[int, float, str]:
    return (-candidate.chispas, candidate.joined_at.timestamp(), candidate.handle)


def choose_champion(candidates: Sequence[ChampionCandidate]) -> ChampionCandidate | None:
    """Función pura: el campeón de una facción entre sus miembros, o None."""
    if not candidates:
        return None
    sponsored = [candidate for candidate in candidates if candidate.sponsored_chispas > 0]
    if sponsored:
        return min(sponsored, key=_by_sponsorship)
    return min(candidates, key=_by_balance)


def _sponsorship_totals(db: Session, season: Season) -> dict[uuid.UUID, tuple[int, datetime]]:
    rows = (
        db.query(Sponsorship.recipient_id, func.sum(Sponsorship.chispas), func.min(Sponsorship.created_at))
        .filter(Sponsorship.season_id == season.id)
        .group_by(Sponsorship.recipient_id)
        .all()
    )
    return {recipient_id: (int(total), first) for recipient_id, total, first in rows}


def faction_candidates(db: Session, season: Season, faction: Faction) -> list[ChampionCandidate]:
    totals = _sponsorship_totals(db, season)
    members = db.query(User).filter(User.faction_id == faction.id).all()
    return [
        ChampionCandidate(
            user_id=member.id,
            handle=member.handle,
            sponsored_chispas=totals.get(member.id, (0, None))[0],
            first_sponsored_at=totals.get(member.id, (0, None))[1],
            chispas=member.chispas,
            joined_at=member.created_at,
        )
        for member in members
    ]


def select_champions(db: Session, season: Season) -> dict[uuid.UUID, uuid.UUID]:
    """{faction_id: user_id} de las facciones que tienen campeón. No escribe nada."""
    chosen: dict[uuid.UUID, uuid.UUID] = {}
    for faction in db.query(Faction).order_by(Faction.slug.asc()).all():
        champion = choose_champion(faction_candidates(db, season, faction))
        if champion is not None:
            chosen[faction.id] = champion.user_id
    return chosen
