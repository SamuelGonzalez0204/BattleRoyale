import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, time, timezone

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.decision import Decision, Vote
from app.models.decision_template import DecisionTemplate
from app.models.season import Season
from app.models.user import UserRole
from app.models.world import WorldState
from app.services.battle_royale.lifecycle import event_blocks_decisions
from app.services.roles import assign_roles_to_unassigned
from app.services.season import world_stats
from app.services.template_selection import next_template
from app.services.world_effects import apply_effects, validate_effects


class BattleRoyaleInProgress(Exception):
    """La Última Luz está en curso (o esperando sello): no hay decisión diaria."""


BATTLE_ROYALE_IN_PROGRESS = "La Última Luz está en curso: hoy no hay decisión diaria"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _end_of_day_utc(day: date) -> datetime:
    return datetime.combine(day, time(23, 59, 59), tzinfo=timezone.utc)


def vote_tallies(db: Session, decision_id: uuid.UUID) -> tuple[int, int]:
    """Suma de pesos (1 + Chispas gastadas) por opción: (votos_a, votos_b)."""
    rows = (
        db.query(Vote.option, func.coalesce(func.sum(Vote.weight), 0))
        .filter(Vote.decision_id == decision_id)
        .group_by(Vote.option)
        .all()
    )
    tallies = {option: int(total) for option, total in rows}
    return tallies.get("a", 0), tallies.get("b", 0)


def pick_winner(votes_a: int, votes_b: int) -> str | None:
    """Gana la opción con más votos ponderados. Empate con votos -> "a"
    (la primera opción, regla fija y determinista). Sin votos -> None."""
    if votes_a == 0 and votes_b == 0:
        return None
    return "b" if votes_b > votes_a else "a"


def _find_decision(db: Session, season: Season, day: date) -> Decision | None:
    return db.query(Decision).filter(Decision.season_id == season.id, Decision.day == day).first()


def _decision_from_template(season: Season, template: DecisionTemplate, day: date) -> Decision:
    return Decision(
        season_id=season.id,
        day=day,
        question=template.question,
        option_a=template.option_a,
        option_b=template.option_b,
        closes_at=_end_of_day_utc(day),
        effects_a=dict(template.effects_a or {}),
        effects_b=dict(template.effects_b or {}),
        role_affinity=template.role_affinity,
        region=template.region,
        template_id=template.id,
    )


def ensure_decision_for_today(
    db: Session, season: Season, today: date | None = None, now: datetime | None = None
) -> Decision:
    """Idempotente: si ya existe la decisión de hoy la devuelve tal cual;
    si no, la crea con la plantilla que elige template_selection (fase y región).
    Antes, cierra cualquier decisión de días anteriores que siga abierta
    (fallback perezoso por si el job de las 23:59 no llegó a correr).
    Mientras haya una Última Luz sin sellar lanza BattleRoyaleInProgress."""
    today = today or _now_utc().date()
    close_open_decisions(db, season, before=today, now=now)
    if event_blocks_decisions(db, season):
        raise BattleRoyaleInProgress(BATTLE_ROYALE_IN_PROGRESS)

    existing = _find_decision(db, season, today)
    if existing is not None:
        return existing

    template = next_template(db, season, today)
    if template is None:
        raise ValueError("No hay plantillas de decisión para la fase actual")

    decision = _decision_from_template(season, template, today)
    db.add(decision)

    try:
        db.commit()
    except IntegrityError:
        # Otra petición concurrente (o el job programado) ya la creó primero.
        db.rollback()
        decision = _find_decision(db, season, today)
        if decision is None:
            raise

    return decision


def _apply_winner_effects(db: Session, decision: Decision, winner: str) -> None:
    state = (
        db.query(WorldState)
        .filter(WorldState.season_id == decision.season_id)
        .with_for_update()
        .first()
    )
    if state is None:
        raise ValueError("La temporada de la decisión no tiene estado de mundo")
    effects = decision.effects_a if winner == "a" else decision.effects_b
    for key, value in apply_effects(world_stats(state), effects or {}).items():
        setattr(state, key, value)


def close_decision(db: Session, decision: Decision, now: datetime | None = None) -> Decision:
    """Cierra la decisión: elige ganador por votos ponderados, aplica sus efectos
    al WorldState de su temporada y da rol a los votantes que ya llegan al umbral.
    Idempotente: si ya estaba cerrada no toca nada. Hace commit."""
    locked = (
        db.query(Decision)
        .filter(Decision.id == decision.id)
        .with_for_update()
        .populate_existing()
        .one()
    )
    if locked.is_closed:
        db.commit()  # libera el bloqueo sin cambios
        return locked

    winner = pick_winner(*vote_tallies(db, locked.id))
    if winner is not None:
        _apply_winner_effects(db, locked, winner)
    locked.winner = winner
    locked.closed_at = now or _now_utc()

    voter_ids = [row[0] for row in db.query(Vote.user_id).filter(Vote.decision_id == locked.id).all()]
    db.flush()
    assign_roles_to_unassigned(db, voter_ids)
    db.commit()
    return locked


def close_open_decisions(
    db: Session, season: Season, before: date, now: datetime | None = None
) -> list[Decision]:
    """Cierra, en orden cronológico, las decisiones abiertas con día < `before`."""
    pending = (
        db.query(Decision)
        .filter(Decision.season_id == season.id, Decision.day < before, Decision.closed_at.is_(None))
        .order_by(Decision.day.asc())
        .all()
    )
    return [close_decision(db, decision, now=now) for decision in pending]


class DecisionHasVotes(Exception):
    """La decisión de hoy ya tiene votos: reemplazarla invalidaría esos votos."""


@dataclass(frozen=True)
class EmergencyDecision:
    question: str
    option_a: str
    option_b: str
    effects_a: Mapping[str, int]
    effects_b: Mapping[str, int]
    role_affinity: UserRole | None


def _has_votes(db: Session, decision_id: uuid.UUID) -> bool:
    return db.query(Vote.id).filter(Vote.decision_id == decision_id).first() is not None


def _fill_decision(decision: Decision, content: EmergencyDecision, day: date) -> None:
    decision.question = content.question
    decision.option_a = content.option_a
    decision.option_b = content.option_b
    decision.effects_a = dict(content.effects_a)
    decision.effects_b = dict(content.effects_b)
    decision.role_affinity = content.role_affinity
    # Escrita a mano: no sale del banco ni está anclada a una región.
    decision.region = None
    decision.template_id = None
    decision.closes_at = _end_of_day_utc(day)
    # Sin votos no se aplicó ningún efecto, así que reabrirla es seguro.
    decision.closed_at = None
    decision.winner = None


def set_emergency_decision(
    db: Session,
    season: Season,
    content: EmergencyDecision,
    today: date | None = None,
    now: datetime | None = None,
) -> Decision:
    """Decisión de hoy escrita a mano por un admin. Si ya existe la de hoy y nadie
    ha votado, se reemplaza en el sitio (mismo id); si tiene votos -> DecisionHasVotes.
    Valida los efectos con world_effects. Hace commit."""
    validate_effects(content.effects_a)
    validate_effects(content.effects_b)
    today = today or _now_utc().date()
    close_open_decisions(db, season, before=today, now=now)

    decision = _find_decision(db, season, today)
    if decision is None:
        decision = Decision(season_id=season.id, day=today)
        db.add(decision)
    elif _has_votes(db, decision.id):
        raise DecisionHasVotes("La decisión de hoy ya tiene votos")
    _fill_decision(decision, content, today)
    db.commit()
    db.refresh(decision)
    return decision
