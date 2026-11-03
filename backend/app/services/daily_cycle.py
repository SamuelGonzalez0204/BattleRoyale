"""Cierre diario del ciclo: cierra la decisión del día, aplica sus efectos,
avanza la fase de la temporada si toca y recalcula roles al cambiar de fase.

Desde la Fase B también mueve La Última Luz (services/battle_royale/lifecycle.py):
tras 7 días de colapso arranca el evento en vez de avanzar de fase, resuelve una
ronda por día y, si nadie eligió sello en 24 h, aplica `eco` y abre la temporada
siguiente. Idempotente: correrlo dos veces el mismo día no resuelve dos rondas."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.season import SeasonPhase
from app.services.battle_royale.lifecycle import BrStep, run_battle_royale_step
from app.services.daily_decision import close_open_decisions
from app.services.roles import recompute_all_roles
from app.services.season import advance_phase_if_due, get_active_season, get_world_state


@dataclass(frozen=True)
class DailyCloseResult:
    closed_decisions: int
    phase_changed: bool
    phase: SeasonPhase
    battle_royale: BrStep | None = None


def run_daily_close(db: Session, now: datetime | None = None) -> DailyCloseResult:
    """Cierra todas las decisiones abiertas hasta hoy (incluida), mueve La Última Luz
    y avanza la fase solo si se cumplió su semana de calendario y no hay evento.
    Lanza ValueError si no hay temporada activa o estado de mundo. Hace commit."""
    now = now or datetime.now(timezone.utc)
    season = get_active_season(db)
    get_world_state(db, season)  # falla rápido si la temporada no tiene mundo
    closed = close_open_decisions(db, season, before=now.date() + timedelta(days=1), now=now)

    step = run_battle_royale_step(db, season, now)
    phase_changed = False
    if step is None:
        phase_changed = advance_phase_if_due(season, now)
        if phase_changed:
            recompute_all_roles(db)
    db.commit()
    current = get_active_season(db)
    return DailyCloseResult(
        closed_decisions=len(closed), phase_changed=phase_changed, phase=current.phase, battle_royale=step
    )
