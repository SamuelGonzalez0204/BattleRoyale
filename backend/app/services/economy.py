import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.chispa import ChispaTransaction
from app.models.user import User


class InsufficientChispas(Exception):
    pass


def utc_day_start(now: datetime) -> datetime:
    return now.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


def capped_award(requested: int, earned_today: int, cap: int) -> int:
    """Chispas que realmente se conceden para no pasar del tope diario."""
    return max(0, min(requested, cap - earned_today))


def chispas_earned_today(db: Session, user_id: uuid.UUID, now: datetime | None = None) -> int:
    """Suma de lo GANADO (importes positivos) en el día UTC actual; gastar no libera tope."""
    day_start = utc_day_start(now or datetime.now(timezone.utc))
    total = db.scalar(
        select(func.coalesce(func.sum(ChispaTransaction.amount), 0)).where(
            ChispaTransaction.user_id == user_id,
            ChispaTransaction.amount > 0,
            ChispaTransaction.created_at >= day_start,
        )
    )
    return int(total or 0)


def _lock_user_row(db: Session, user_id: uuid.UUID) -> None:
    # Serializa premios concurrentes de la misma cuenta para que el tope no se salte.
    db.execute(select(User.id).where(User.id == user_id).with_for_update())


def award_chispas(
    db: Session,
    user: User,
    amount: int,
    reason: str,
    daily_cap: int | None = None,
) -> int:
    """Concede Chispas respetando las reglas anti-abuso y devuelve cuántas se dieron.

    - Cuentas sin email verificado no ganan nada.
    - Nunca se supera el tope diario (settings.chispas_daily_earn_cap por defecto).
    """
    if amount <= 0:
        raise ValueError("amount debe ser positivo")
    if not user.is_verified:
        return 0

    cap = get_settings().chispas_daily_earn_cap if daily_cap is None else daily_cap
    db.flush()
    _lock_user_row(db, user.id)
    granted = capped_award(amount, chispas_earned_today(db, user.id), cap)
    if granted == 0:
        return 0

    user.chispas += granted
    db.add(ChispaTransaction(user_id=user.id, amount=granted, reason=reason))
    db.flush()
    return granted


def spend_chispas(db: Session, user: User, amount: int, reason: str) -> None:
    if amount <= 0:
        raise ValueError("amount debe ser positivo")
    if user.chispas < amount:
        raise InsufficientChispas(f"El usuario tiene {user.chispas} Chispas, pide gastar {amount}")
    user.chispas -= amount
    db.add(ChispaTransaction(user_id=user.id, amount=-amount, reason=reason))
