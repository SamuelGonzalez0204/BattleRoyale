"""Ciclo de vida de La Última Luz, enganchado al cierre diario de las 23:59.

1. Cuando la temporada lleva EVENT_START_DELAY (7 días) en `colapso`, el cierre
   diario arranca el evento en vez de avanzar de fase: elige campeones (uno por
   facción con miembros, ver champions.py) y abre el duelo de la ronda 1, que se
   resuelve en el cierre del día siguiente. Hacen falta al menos MIN_CHAMPIONS
   facciones con miembros; si no, no arranca y se reintenta al día siguiente.
2. Con el evento `active`, cada cierre diario resuelve el duelo del día (rounds.py):
   rondas 1–6 en las regiones que caen (herida solo con un margen del 15 %, ver
   resolution.py) y la 7 en la Arena, el duelo final que decide por puntos.
   Mientras haya un evento sin sellar no se generan decisiones diarias.
3. Con el evento `finished`, si nadie eligió sello en 24 h, el cierre diario
   aplica `eco` y abre la temporada siguiente (seals.py).
Todas las transiciones bloquean filas y son idempotentes.
"""

import enum
import logging
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.battle_royale import BattleRoyaleEvent, BrEventStatus, BrSeal, Champion
from app.models.season import Season, SeasonPhase
from app.services.battle_royale.champions import select_champions
from app.services.battle_royale.rounds import NoActiveRound, open_duel, resolve_current_round
from app.services.battle_royale.seals import DEFAULT_SEAL, apply_seal, seal_is_overdue

EVENT_START_DELAY = timedelta(days=7)
MIN_CHAMPIONS = 2

logger = logging.getLogger("el_ciclo.battle_royale")


class EventAlreadyExists(Exception):
    """La temporada ya tiene (o tuvo) su Última Luz."""


class NotEnoughChampions(Exception):
    """Hacen falta al menos MIN_CHAMPIONS facciones con miembros."""


class BrStep(str, enum.Enum):
    started = "started"
    round_resolved = "round_resolved"
    waiting = "waiting"  # evento en curso o esperando sello: nada que hacer hoy
    sealed = "sealed"


def is_battle_royale_due(phase: SeasonPhase, phase_started_at: datetime, now: datetime) -> bool:
    """Regla pura: ¿toca arrancar La Última Luz?"""
    return SeasonPhase(phase) == SeasonPhase.colapso and now >= phase_started_at + EVENT_START_DELAY


def event_for_season(db: Session, season: Season) -> BattleRoyaleEvent | None:
    return db.query(BattleRoyaleEvent).filter(BattleRoyaleEvent.season_id == season.id).first()


def event_blocks_decisions(db: Session, season: Season) -> bool:
    """True si la temporada tiene una Última Luz sin sellar (no hay decisiones diarias)."""
    event = event_for_season(db, season)
    return event is not None and event.status != BrEventStatus.sealed


def start_event(db: Session, season: Season, now: datetime) -> BattleRoyaleEvent:
    """Crea el evento con sus campeones y el duelo de la ronda 1. Bloquea la
    temporada; lanza EventAlreadyExists o NotEnoughChampions. Hace commit."""
    locked = db.query(Season).filter(Season.id == season.id).with_for_update().one()
    if event_for_season(db, locked) is not None:
        db.rollback()
        raise EventAlreadyExists("Esta temporada ya tiene su Última Luz")
    champions = select_champions(db, locked)
    if len(champions) < MIN_CHAMPIONS:
        db.rollback()
        raise NotEnoughChampions(
            f"Hacen falta al menos {MIN_CHAMPIONS} facciones con miembros para La Última Luz"
        )

    event = BattleRoyaleEvent(season_id=locked.id, status=BrEventStatus.active, round_number=1,
                              fallen_zones=[], started_at=now)
    db.add(event)
    db.flush()
    for faction_id, user_id in champions.items():
        db.add(Champion(event_id=event.id, faction_id=faction_id, user_id=user_id, wounds=0, total_score=0.0))
    open_duel(db, event, 1, now.date())
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()  # otra petición/job lo creó a la vez (uq en season_id)
        raise EventAlreadyExists("Esta temporada ya tiene su Última Luz") from exc
    return event


def _step_active(db: Session, event: BattleRoyaleEvent, now: datetime) -> BrStep:
    try:
        duel = resolve_current_round(db, event.id, now)
    except NoActiveRound:
        return BrStep.waiting
    return BrStep.round_resolved if duel is not None else BrStep.waiting


def _step_finished(db: Session, event: BattleRoyaleEvent, now: datetime) -> BrStep:
    if event.seal_deadline is None or not seal_is_overdue(event.seal_deadline, now):
        return BrStep.waiting
    apply_seal(db, event.id, BrSeal(DEFAULT_SEAL), now, chosen_by=None)
    return BrStep.sealed


def _maybe_start(db: Session, season: Season, now: datetime) -> BrStep | None:
    if not is_battle_royale_due(season.phase, season.phase_started_at, now):
        return None
    try:
        start_event(db, season, now)
    except NotEnoughChampions as exc:
        logger.warning("La Última Luz no arranca: %s", exc)
        return BrStep.waiting
    except EventAlreadyExists:
        return BrStep.waiting
    return BrStep.started


def run_battle_royale_step(db: Session, season: Season, now: datetime) -> BrStep | None:
    """Paso diario. None = la temporada sigue su ciclo normal de fases."""
    event = event_for_season(db, season)
    if event is None:
        return _maybe_start(db, season, now)
    if event.status == BrEventStatus.active:
        return _step_active(db, event, now)
    if event.status == BrEventStatus.finished:
        return _step_finished(db, event, now)
    return BrStep.waiting
