from sqlalchemy.orm import Session

from app.models.chispa import ChispaTransaction
from app.models.user import User


class InsufficientChispas(Exception):
    pass


def award_chispas(db: Session, user: User, amount: int, reason: str) -> None:
    if amount <= 0:
        raise ValueError("amount debe ser positivo")
    user.chispas += amount
    db.add(ChispaTransaction(user_id=user.id, amount=amount, reason=reason))


def spend_chispas(db: Session, user: User, amount: int, reason: str) -> None:
    if amount <= 0:
        raise ValueError("amount debe ser positivo")
    if user.chispas < amount:
        raise InsufficientChispas(f"El usuario tiene {user.chispas} Chispas, pide gastar {amount}")
    user.chispas -= amount
    db.add(ChispaTransaction(user_id=user.id, amount=-amount, reason=reason))
