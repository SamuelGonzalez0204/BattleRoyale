"""Qué plantilla del banco sale hoy (Fase E).

Regla pura (`choose_template`) + la consulta que le prepara los candidatos.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.decision import Decision
from app.models.decision_template import DecisionTemplate
from app.models.season import Season, SeasonPhase


@dataclass(frozen=True)
class TemplateCandidate:
    id: uuid.UUID
    order: int
    phase: SeasonPhase | None
    used_this_season: bool
    last_used_on: date | None


def _fresh_key(candidate: TemplateCandidate) -> tuple[bool, int]:
    # Primero las propias de la fase; las genéricas (phase NULL) de reserva.
    return candidate.phase is None, candidate.order


def _recycle_key(candidate: TemplateCandidate) -> tuple[date, bool, int]:
    return candidate.last_used_on or date.min, candidate.phase is None, candidate.order


def choose_template(
    candidates: Sequence[TemplateCandidate],
    phase: SeasonPhase,
    yesterday_id: uuid.UUID | None,
) -> uuid.UUID | None:
    """Plantilla para hoy, o None si ninguna vale para `phase`.

    1. Solo valen las de `phase` o las genéricas (phase None).
    2. Nunca la de ayer, salvo que sea la única posible.
    3. Antes las no usadas en esta temporada (las de la fase primero, por `order`).
    4. Agotadas: se recicla la usada hace más tiempo (nunca usada = la más antigua).
    """
    eligible = [c for c in candidates if c.phase is None or c.phase == phase]
    if len(eligible) > 1:
        eligible = [c for c in eligible if c.id != yesterday_id]
    if not eligible:
        return None
    fresh = [c for c in eligible if not c.used_this_season]
    if fresh:
        return min(fresh, key=_fresh_key).id
    return min(eligible, key=_recycle_key).id


def _yesterday_template_id(db: Session, today: date) -> uuid.UUID | None:
    """Plantilla de la decisión más reciente anterior a hoy, de cualquier temporada."""
    row = (
        db.query(Decision.template_id)
        .filter(Decision.day < today, Decision.template_id.is_not(None))
        .order_by(Decision.day.desc())
        .first()
    )
    return row[0] if row else None


def load_candidates(db: Session, season: Season) -> list[TemplateCandidate]:
    """Todas las plantillas con su uso en la temporada y su último día de uso (2 consultas)."""
    last_used = dict(
        db.query(Decision.template_id, func.max(Decision.day))
        .filter(Decision.template_id.is_not(None))
        .group_by(Decision.template_id)
        .all()
    )
    used_in_season = {
        row[0]
        for row in db.query(Decision.template_id)
        .filter(Decision.season_id == season.id, Decision.template_id.is_not(None))
        .distinct()
    }
    templates = db.query(DecisionTemplate.id, DecisionTemplate.order, DecisionTemplate.phase).all()
    return [
        TemplateCandidate(
            id=template_id,
            order=order,
            phase=phase,
            used_this_season=template_id in used_in_season,
            last_used_on=last_used.get(template_id),
        )
        for template_id, order, phase in templates
    ]


def next_template(db: Session, season: Season, today: date) -> DecisionTemplate | None:
    chosen = choose_template(load_candidates(db, season), season.phase, _yesterday_template_id(db, today))
    return db.get(DecisionTemplate, chosen) if chosen is not None else None
