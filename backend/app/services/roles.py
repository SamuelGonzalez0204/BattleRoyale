"""Roles: tras votar suficientes decisiones, cada usuario recibe el rol cuya
etiqueta (role_affinity de la decisión) más ha votado."""

import uuid
from collections.abc import Iterable, Mapping

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.decision import Decision, Vote
from app.models.user import User, UserRole

MIN_VOTES_FOR_ROLE = 5
# Orden fijo para desempatar: gana el primero de esta lista.
ROLE_ORDER: tuple[str, ...] = tuple(role.value for role in UserRole)


def choose_role(affinity_counts: Mapping[str, int]) -> str | None:
    """Función pura: rol con más votos, o None si aún no llega al umbral.
    Empates: se resuelven por ROLE_ORDER (mercader > guardia > cronista > explorador)."""
    known = {role: int(affinity_counts.get(role, 0)) for role in ROLE_ORDER}
    if sum(known.values()) < MIN_VOTES_FOR_ROLE:
        return None
    return max(ROLE_ORDER, key=lambda role: (known[role], -ROLE_ORDER.index(role)))


def affinity_counts_for_user(db: Session, user_id: uuid.UUID) -> dict[str, int]:
    rows = (
        db.query(Decision.role_affinity, func.count(Vote.id))
        .join(Vote, Vote.decision_id == Decision.id)
        .filter(Vote.user_id == user_id, Decision.role_affinity.is_not(None))
        .group_by(Decision.role_affinity)
        .all()
    )
    return {UserRole(affinity).value: int(count) for affinity, count in rows}


def assign_role(db: Session, user: User) -> bool:
    """Recalcula el rol de un usuario. Devuelve True si ha cambiado. No hace commit."""
    chosen = choose_role(affinity_counts_for_user(db, user.id))
    if chosen is None:
        return False
    new_role = UserRole(chosen)
    if user.role == new_role:
        return False
    user.role = new_role
    return True


def assign_roles_to_unassigned(db: Session, user_ids: Iterable[uuid.UUID]) -> int:
    """Da rol a los usuarios indicados que todavía no tienen. No hace commit."""
    ids = list(user_ids)
    if not ids:
        return 0
    users = db.query(User).filter(User.id.in_(ids), User.role.is_(None)).all()
    return sum(1 for user in users if assign_role(db, user))


def recompute_all_roles(db: Session) -> int:
    """Recalcula el rol de todo el que ha votado (se usa en cada cambio de fase).
    No hace commit."""
    voter_ids = db.query(Vote.user_id).distinct()
    users = db.query(User).filter(User.id.in_(voter_ids)).all()
    return sum(1 for user in users if assign_role(db, user))
