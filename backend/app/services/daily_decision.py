from datetime import date, datetime, time, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.decision import Decision
from app.models.decision_template import DecisionTemplate
from app.models.season import Season


def _end_of_today_utc() -> datetime:
    return datetime.combine(date.today(), time(23, 59, 59), tzinfo=timezone.utc)


def _next_template(db: Session) -> DecisionTemplate | None:
    template = (
        db.query(DecisionTemplate)
        .filter(DecisionTemplate.used.is_(False))
        .order_by(DecisionTemplate.order.asc())
        .first()
    )
    if template is not None:
        return template

    # Se agotó el banco de preguntas: se recicla entero y se vuelve a empezar.
    db.query(DecisionTemplate).update({DecisionTemplate.used: False})
    db.flush()
    return db.query(DecisionTemplate).order_by(DecisionTemplate.order.asc()).first()


def ensure_decision_for_today(db: Session, season: Season) -> Decision:
    """Idempotente: si ya existe la decisión de hoy la devuelve tal cual;
    si no, la crea a partir de la siguiente plantilla sin usar del banco."""
    today = date.today()
    existing = (
        db.query(Decision)
        .filter(Decision.season_id == season.id, Decision.day == today)
        .first()
    )
    if existing is not None:
        return existing

    template = _next_template(db)
    if template is None:
        raise ValueError("No hay plantillas de decisión configuradas todavía")

    decision = Decision(
        season_id=season.id,
        day=today,
        question=template.question,
        option_a=template.option_a,
        option_b=template.option_b,
        closes_at=_end_of_today_utc(),
    )
    template.used = True
    db.add(decision)

    try:
        db.commit()
    except IntegrityError:
        # Otra petición concurrente (o el job programado) ya la creó primero.
        db.rollback()
        decision = (
            db.query(Decision)
            .filter(Decision.season_id == season.id, Decision.day == today)
            .first()
        )
        if decision is None:
            raise

    return decision
