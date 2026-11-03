"""Cierre diario del ciclo: cierra la decisión del día, aplica sus efectos,
avanza la fase de la temporada si toca y recalcula roles al cambiar de fase."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.season import SeasonPhase
from app.services.daily_decision import close_open_decisions
from app.services.roles import recompute_all_roles
from app.services.season import advance_phase_if_due, get_active_season, get_world_state


@dataclass(frozen=True)
class DailyCloseResult:
    closed_decisions: int
    phase_changed: bool
    phase: SeasonPhase


def run_daily_close(db: Session, now: datetime | None = None) -> DailyCloseResult:
    """Cierra todas las decisiones abiertas hasta hoy (incluida) y avanza la fase
    solo si se cumplió su semana de calendario. Lanza ValueError si no hay
    temporada activa o estado de mundo. Hace commit."""
    now = now or datetime.now(timezone.utc)
    season = get_active_season(db)
    get_world_state(db, season)  # falla rápido si la temporada no tiene mundo
    closed = close_open_decisions(db, season, before=now.date() + timedelta(days=1), now=now)

    phase_changed = advance_phase_if_due(season, now)
    if phase_changed:
        recompute_all_roles(db)
    db.commit()
    return DailyCloseResult(closed_decisions=len(closed), phase_changed=phase_changed, phase=season.phase)
