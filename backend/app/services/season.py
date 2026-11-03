from datetime import datetime, timedelta
from typing import Protocol

from sqlalchemy.orm import Session

from app.models.season import Season, SeasonPhase
from app.models.world import WorldState
from app.services.world_effects import STAT_KEYS

PHASE_DURATION = timedelta(days=7)
PHASE_ORDER: tuple[SeasonPhase, ...] = (
    SeasonPhase.construccion,
    SeasonPhase.conflicto,
    SeasonPhase.convergencia,
    SeasonPhase.colapso,
)


class PhasedSeason(Protocol):
    phase: SeasonPhase
    phase_started_at: datetime


def get_active_season(db: Session) -> Season:
    season = db.query(Season).filter(Season.is_active.is_(True)).order_by(Season.number.desc()).first()
    if season is None:
        raise ValueError("No hay una temporada activa configurada")
    return season


def get_world_state(db: Session, season: Season) -> WorldState:
    state = db.query(WorldState).filter(WorldState.season_id == season.id).first()
    if state is None:
        raise ValueError("La temporada activa no tiene estado de mundo todavía")
    return state


def world_stats(state: WorldState) -> dict[str, int]:
    return {key: getattr(state, key) for key in STAT_KEYS}


def _following_phase(phase: SeasonPhase) -> SeasonPhase | None:
    index = PHASE_ORDER.index(SeasonPhase(phase))
    return PHASE_ORDER[index + 1] if index + 1 < len(PHASE_ORDER) else None


def next_phase_transition(
    phase: SeasonPhase,
    phase_started_at: datetime,
    now: datetime,
) -> tuple[SeasonPhase, datetime] | None:
    """Regla pura: devuelve (fase_siguiente, inicio_de_esa_fase) o None.

    Solo por calendario: una fase cada PHASE_DURATION. La nueva fase arranca en
    phase_started_at + PHASE_DURATION (mantiene la cadencia aunque el job llegue
    tarde). Las stats del mundo no adelantan la fase. Colapso es la última fase:
    nunca se pasa de ahí.
    """
    following = _following_phase(phase)
    if following is None:
        return None
    due_at = phase_started_at + PHASE_DURATION
    if now >= due_at:
        return following, due_at
    return None


def advance_phase_if_due(season: PhasedSeason, now: datetime) -> bool:
    """Avanza como mucho una fase. Devuelve True si la fase cambió. No hace commit."""
    transition = next_phase_transition(season.phase, season.phase_started_at, now)
    if transition is None:
        return False
    season.phase, season.phase_started_at = transition
    return True
