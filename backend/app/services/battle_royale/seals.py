"""Sellos de La Última Luz y reset de temporada.

Al acabar el evento, el campeón ganador (o un admin) elige un sello en las 24 h
siguientes (SEAL_WINDOW). Si nadie lo elige, el cierre diario aplica `eco`. El
sello suma +15 a una stat del mundo de la temporada siguiente, que arranca desde
la misma base que la siembra inicial (services/season.WORLD_BASELINE).
"""

import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.battle_royale import BattleRoyaleEvent, BrEventStatus, BrSeal, Champion
from app.models.season import Season
from app.models.user import User
from app.services.season import start_next_season

SEAL_BONUS = 15
SEAL_BONUSES: dict[str, dict[str, int]] = {
    "abundancia": {"comida": SEAL_BONUS},
    "muralla": {"defensa": SEAL_BONUS},
    "oro": {"oro": SEAL_BONUS},
    "eco": {"moral": SEAL_BONUS},
    "cuna": {"poblacion": SEAL_BONUS},
}
DEFAULT_SEAL = BrSeal.eco.value
SEAL_WINDOW = timedelta(hours=24)


class SealNotAvailable(Exception):
    """El evento no está esperando sello (sigue en curso o ya se selló)."""


class SealForbidden(Exception):
    """Solo el campeón ganador (dentro del plazo) o un admin pueden elegir el sello."""


def seal_deadline(finished_at: datetime) -> datetime:
    return finished_at + SEAL_WINDOW


def seal_is_overdue(deadline: datetime, now: datetime) -> bool:
    return now >= deadline


def winning_champion_user_id(db: Session, event: BattleRoyaleEvent) -> uuid.UUID | None:
    if event.winner_faction_id is None:
        return None
    champion = (
        db.query(Champion)
        .filter(Champion.event_id == event.id, Champion.faction_id == event.winner_faction_id)
        .first()
    )
    return champion.user_id if champion else None


def _lock_event(db: Session, event_id: uuid.UUID) -> BattleRoyaleEvent:
    return (
        db.query(BattleRoyaleEvent)
        .filter(BattleRoyaleEvent.id == event_id)
        .with_for_update()
        .populate_existing()
        .one()
    )


def _check_chooser(db: Session, event: BattleRoyaleEvent, user: User | None, now: datetime) -> None:
    if user is None or user.is_admin:
        return
    if winning_champion_user_id(db, event) != user.id:
        raise SealForbidden("Solo el campeón ganador o un admin pueden elegir el sello")
    if event.seal_deadline is not None and seal_is_overdue(event.seal_deadline, now):
        raise SealForbidden("El plazo de 24 horas para elegir el sello ya venció")


def apply_seal(
    db: Session, event_id: uuid.UUID, seal: BrSeal, now: datetime, chosen_by: User | None = None
) -> Season:
    """Fija el sello, cierra la temporada del evento y crea la siguiente con el bonus.
    `chosen_by=None` es el sello automático del job. Idempotencia: un evento ya
    sellado lanza SealNotAvailable. Hace commit y devuelve la temporada nueva."""
    event = _lock_event(db, event_id)
    if event.status != BrEventStatus.finished:
        db.rollback()
        detail = "El sello ya se eligió" if event.status == BrEventStatus.sealed else "La Última Luz sigue en curso"
        raise SealNotAvailable(detail)
    try:
        _check_chooser(db, event, chosen_by, now)
    except SealForbidden:
        db.rollback()
        raise

    old_season = db.query(Season).filter(Season.id == event.season_id).with_for_update().one()
    new_season = start_next_season(db, old_season, SEAL_BONUSES[seal.value], now)
    event.seal = seal
    event.sealed_at = now
    event.sealed_by_id = chosen_by.id if chosen_by else None
    event.status = BrEventStatus.sealed
    event.next_season_id = new_season.id
    db.commit()
    return new_season
