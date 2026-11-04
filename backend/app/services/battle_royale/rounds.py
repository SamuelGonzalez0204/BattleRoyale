"""Rondas de La Última Luz en BD: crear el duelo de cada ronda y resolverlo.

Cada ronda tiene un único `Duel`, situado en la zona que cae esa ronda, con todos
los campeones vivos. La ronda 7 (la Arena) es el duelo final: puntúa pero no hiere.
Lo resuelve el cierre diario de las 23:59 del día
`Duel.resolves_on` (o un admin antes). La resolución usa la función pura
`resolution.resolve_round`; aquí solo se leen votos/miembros y se escriben
heridas, puntuaciones, zonas caídas y, si toca, el final del evento.
"""

import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.battle_royale import BattleRoyaleEvent, BrEventStatus, Champion, Duel, TacticVote
from app.models.faction import Faction
from app.models.user import User
from app.services.battle_royale.resolution import (
    Contender,
    RoundOutcome,
    Standing,
    event_is_over,
    is_alive,
    pick_event_winner,
    resolve_round,
)
from app.services.battle_royale.seals import seal_deadline
from app.services.battle_royale.zones import TOTAL_ROUNDS, zone_falls, zone_for_round


class NoActiveRound(Exception):
    """No hay evento en curso con un duelo pendiente."""


def open_duel(db: Session, event: BattleRoyaleEvent, round_number: int, today: date) -> Duel:
    """Crea el duelo de la ronda; se resolverá en el cierre del día siguiente. No hace commit."""
    duel = Duel(
        event_id=event.id,
        round_number=round_number,
        zone=zone_for_round(round_number),
        resolves_on=today + timedelta(days=1),
    )
    db.add(duel)
    db.flush()
    return duel


def current_duel(db: Session, event: BattleRoyaleEvent) -> Duel | None:
    return (
        db.query(Duel)
        .filter(Duel.event_id == event.id, Duel.round_number == event.round_number)
        .first()
    )


def champions_with_slugs(db: Session, event_id: uuid.UUID) -> list[tuple[Champion, str]]:
    return (
        db.query(Champion, Faction.slug)
        .join(Faction, Faction.id == Champion.faction_id)
        .filter(Champion.event_id == event_id)
        .order_by(Faction.slug.asc())
        .all()
    )


def faction_member_counts(db: Session, faction_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    rows = (
        db.query(User.faction_id, func.count(User.id))
        .filter(User.faction_id.in_(faction_ids))
        .group_by(User.faction_id)
        .all()
    )
    return {faction_id: int(count) for faction_id, count in rows}


def tactic_weights_by_faction(db: Session, duel_id: uuid.UUID) -> dict[uuid.UUID, dict[str, int]]:
    rows = (
        db.query(TacticVote.faction_id, TacticVote.tactic, func.sum(TacticVote.weight))
        .filter(TacticVote.duel_id == duel_id)
        .group_by(TacticVote.faction_id, TacticVote.tactic)
        .all()
    )
    weights: dict[uuid.UUID, dict[str, int]] = defaultdict(dict)
    for faction_id, tactic, total in rows:
        weights[faction_id][tactic.value] = int(total)
    return weights


def _contenders(db: Session, duel: Duel, alive: list[tuple[Champion, str]]) -> list[Contender]:
    faction_ids = [champion.faction_id for champion, _ in alive]
    members = faction_member_counts(db, faction_ids)
    weights = tactic_weights_by_faction(db, duel.id)
    return [
        Contender(
            faction_slug=slug,
            members=members.get(champion.faction_id, 0),
            wounds=champion.wounds,
            tactic_weights=weights.get(champion.faction_id, {}),
        )
        for champion, slug in alive
    ]


def _result_payload(outcome: RoundOutcome) -> dict:
    return {
        "wounded": outcome.wounded_faction,
        "reason": outcome.reason,
        "factions": [
            {
                "faction_slug": item.faction_slug,
                "tactic": item.tactic,
                "total_weight": item.total_weight,
                "participation": item.participation,
                "wins": item.wins,
                "score": item.score,
                "wounded": item.wounded,
            }
            for item in outcome.outcomes
        ],
    }


def _apply_outcome(duel: Duel, alive: list[tuple[Champion, str]], outcome: RoundOutcome) -> None:
    for champion, slug in alive:
        result = outcome.outcome_for(slug)
        champion.total_score = round(champion.total_score + result.score, 6)
        if result.wounded:
            champion.wounds += 1
            duel.wounded_champion_id = champion.id
            if not is_alive(champion.wounds):
                champion.eliminated_round = duel.round_number


def finish_event(db: Session, event: BattleRoyaleEvent, now: datetime) -> None:
    """Marca el evento como terminado con su ganador y abre el plazo del sello. No hace commit."""
    standings = champions_with_slugs(db, event.id)
    winner_slug = pick_event_winner(
        [Standing(slug, champion.wounds, champion.total_score) for champion, slug in standings]
    )
    by_slug = {slug: champion for champion, slug in standings}
    event.winner_faction_id = by_slug[winner_slug].faction_id if winner_slug else None
    event.status = BrEventStatus.finished
    event.finished_at = now
    event.seal_deadline = seal_deadline(now)


def _lock_active_event(db: Session, event_id: uuid.UUID) -> BattleRoyaleEvent:
    event = (
        db.query(BattleRoyaleEvent)
        .filter(BattleRoyaleEvent.id == event_id)
        .with_for_update()
        .populate_existing()
        .one()
    )
    if event.status != BrEventStatus.active:
        raise NoActiveRound("La Última Luz no tiene ninguna ronda en curso")
    return event


def _lock_duel(db: Session, event: BattleRoyaleEvent) -> Duel:
    duel = (
        db.query(Duel)
        .filter(Duel.event_id == event.id, Duel.round_number == event.round_number)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if duel is None or duel.is_resolved:
        raise NoActiveRound("La ronda actual no tiene un duelo pendiente")
    return duel


def resolve_current_round(
    db: Session, event_id: uuid.UUID, now: datetime, force: bool = False
) -> Duel | None:
    """Resuelve el duelo de la ronda en curso. Sin `force` solo si ya llegó su día
    (`resolves_on <= now.date()`); si no, no toca nada y devuelve None. Bloquea el
    evento y el duelo (idempotente frente a jobs/peticiones concurrentes). Abre la
    ronda siguiente o termina el evento. Lanza NoActiveRound. Hace commit."""
    try:
        event = _lock_active_event(db, event_id)
        duel = _lock_duel(db, event)
    except NoActiveRound:
        db.rollback()
        raise
    if not force and duel.resolves_on > now.date():
        db.commit()  # libera los bloqueos sin cambios
        return None

    champions = champions_with_slugs(db, event.id)
    alive = [(champion, slug) for champion, slug in champions if is_alive(champion.wounds)]
    outcome = resolve_round(_contenders(db, duel, alive), is_final=duel.round_number == TOTAL_ROUNDS)
    _apply_outcome(duel, alive, outcome)
    duel.result = _result_payload(outcome)
    duel.resolved_at = now
    if zone_falls(duel.zone):
        event.fallen_zones = [*event.fallen_zones, duel.zone]

    survivors = sum(1 for champion, _ in champions if is_alive(champion.wounds))
    if event_is_over(survivors, duel.round_number):
        finish_event(db, event, now)
    else:
        event.round_number = duel.round_number + 1
        open_duel(db, event, event.round_number, now.date())
    db.commit()
    return duel
