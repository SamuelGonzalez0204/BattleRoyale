from collections.abc import Mapping
from datetime import datetime, timedelta
from types import MappingProxyType
from typing import Protocol

from sqlalchemy.orm import Session

from app.models.season import Season, SeasonPhase
from app.models.world import WorldState
from app.services.roles import recompute_all_roles
from app.services.world_effects import STAT_KEYS, apply_effects

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


class FinalPhaseReached(ValueError):
    """Colapso es la última fase: no hay a dónde avanzar."""


def following_phase(phase: SeasonPhase) -> SeasonPhase | None:
    """Fase que viene después de `phase`, o None si ya es la última (colapso)."""
    return _following_phase(phase)


def force_advance_phase(season: PhasedSeason, now: datetime) -> SeasonPhase:
    """Avance manual (admin): pasa a la fase siguiente ya, sin esperar al calendario.
    El reloj de la fase se reinicia en `now`. Nunca pasa de colapso. No hace commit."""
    following = _following_phase(season.phase)
    if following is None:
        raise FinalPhaseReached("La temporada ya está en colapso, la última fase")
    season.phase, season.phase_started_at = following, now
    return following


def advance_phase_if_due(season: PhasedSeason, now: datetime) -> bool:
    """Avanza como mucho una fase. Devuelve True si la fase cambió. No hace commit."""
    transition = next_phase_transition(season.phase, season.phase_started_at, now)
    if transition is None:
        return False
    season.phase, season.phase_started_at = transition
    return True


# --- Reset de temporada (Fase B) ---------------------------------------------

# Misma base que la siembra de la Temporada 1 (migración 0002).
WORLD_BASELINE: Mapping[str, int] = MappingProxyType(
    {"poblacion": 68, "comida": 41, "moral": 55, "defensa": 72, "oro": 36}
)


def next_season_world(seal_effects: Mapping[str, int]) -> dict[str, int]:
    """Regla pura: stats iniciales de la temporada siguiente = base + bonus del sello
    (recortado a 0–100 por apply_effects). No modifica WORLD_BASELINE."""
    return apply_effects(WORLD_BASELINE, seal_effects)


def start_next_season(
    db: Session, previous: Season, seal_effects: Mapping[str, int], now: datetime
) -> Season:
    """Cierra `previous` y abre la Temporada N+1 (activa, en construcción desde `now`)
    con un WorldState nuevo desde WORLD_BASELINE + sello. Las facciones y las
    Chispas de los usuarios no se tocan. Recalcula roles. No hace commit."""
    previous.is_active = False
    previous.ended_at = now
    number = previous.number + 1
    season = Season(
        number=number,
        name=f"Temporada {number}",
        phase=SeasonPhase.construccion,
        is_active=True,
        started_at=now,
        phase_started_at=now,
    )
    db.add(season)
    db.flush()
    db.add(WorldState(season_id=season.id, **next_season_world(seal_effects)))
    recompute_all_roles(db)
    db.flush()
    return season
