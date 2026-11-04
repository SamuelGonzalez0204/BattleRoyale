"""Votos de táctica en los duelos de La Última Luz.

Un voto por usuario y duelo (no se cambia). Solo votan miembros de facciones con
campeón vivo, mientras el duelo de la ronda en curso no se haya resuelto. Peso =
1 + Chispas gastadas (gasto vía economy.spend_chispas, nunca deja saldo negativo).
Antes de resolverse, cada facción solo ve los totales de la suya.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.battle_royale import BattleRoyaleEvent, BrEventStatus, BrTactic, Champion, Duel, TacticVote
from app.models.user import User
from app.services.battle_royale.resolution import TACTIC_ORDER, is_alive
from app.services.economy import spend_chispas

TACTIC_VOTE_REASON = "voto_tactica"


class DuelNotFound(Exception):
    pass


class DuelClosed(Exception):
    """El duelo ya se resolvió o no es el de la ronda en curso."""


class NotEligible(Exception):
    """El usuario no tiene facción o su campeón ya cayó."""


class AlreadyVoted(Exception):
    pass


@dataclass(frozen=True)
class FactionTotals:
    weights: dict[str, int]
    voters: int


def faction_totals(db: Session, duel_id: uuid.UUID, faction_id: uuid.UUID) -> FactionTotals:
    rows = (
        db.query(TacticVote.tactic, func.sum(TacticVote.weight), func.count(TacticVote.id))
        .filter(TacticVote.duel_id == duel_id, TacticVote.faction_id == faction_id)
        .group_by(TacticVote.tactic)
        .all()
    )
    weights = {tactic: 0 for tactic in TACTIC_ORDER}
    voters = 0
    for tactic, total, count in rows:
        weights[tactic.value] = int(total)
        voters += int(count)
    return FactionTotals(weights=weights, voters=voters)


def find_vote(db: Session, duel_id: uuid.UUID, user_id: uuid.UUID) -> TacticVote | None:
    return db.query(TacticVote).filter(TacticVote.duel_id == duel_id, TacticVote.user_id == user_id).first()


def faction_has_alive_champion(db: Session, event_id: uuid.UUID, faction_id: uuid.UUID | None) -> bool:
    if faction_id is None:
        return False
    champion = (
        db.query(Champion).filter(Champion.event_id == event_id, Champion.faction_id == faction_id).first()
    )
    return champion is not None and is_alive(champion.wounds)


def _lock_open_duel(db: Session, duel_id: uuid.UUID) -> Duel:
    duel = db.query(Duel).filter(Duel.id == duel_id).with_for_update().populate_existing().first()
    if duel is None:
        raise DuelNotFound("Ese duelo no existe")
    event = db.get(BattleRoyaleEvent, duel.event_id)
    if (
        duel.is_resolved
        or event is None
        or event.status != BrEventStatus.active
        or event.round_number != duel.round_number
    ):
        raise DuelClosed("Este duelo ya está cerrado")
    return duel


def _check_voter(db: Session, duel: Duel, user: User) -> None:
    if user.faction_id is None:
        raise NotEligible("Necesitas una facción para votar en La Última Luz")
    if not faction_has_alive_champion(db, duel.event_id, user.faction_id):
        raise NotEligible("El campeón de tu facción ya cayó: no puedes votar")
    if find_vote(db, duel.id, user.id) is not None:
        raise AlreadyVoted("Ya votaste en este duelo")


def cast_tactic_vote(
    db: Session, duel_id: uuid.UUID, user: User, tactic: BrTactic, chispas_to_spend: int
) -> TacticVote:
    """Registra el voto. Lanza DuelNotFound, DuelClosed, NotEligible, AlreadyVoted o
    economy.InsufficientChispas (en todos los casos sin cambios). Hace commit."""
    try:
        duel = _lock_open_duel(db, duel_id)
        _check_voter(db, duel, user)
        if chispas_to_spend > 0:
            spend_chispas(db, user, chispas_to_spend, reason=TACTIC_VOTE_REASON)
    except Exception:
        db.rollback()
        raise

    vote = TacticVote(
        duel_id=duel.id,
        user_id=user.id,
        faction_id=user.faction_id,
        tactic=tactic,
        chispas_spent=chispas_to_spend,
        weight=1 + chispas_to_spend,
    )
    db.add(vote)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()  # doble clic concurrente: manda el índice único
        raise AlreadyVoted("Ya votaste en este duelo") from exc
    return vote
