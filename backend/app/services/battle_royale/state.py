"""Vista de GET /api/br/state para un usuario concreto.

Evento mostrado: el de la temporada activa; si no tiene, el de la temporada
anterior ya sellado (status "sealed": así el frontend puede contar con qué sello
nació la temporada actual). Sin ninguno → status "none".
Antes de resolverse un duelo solo se exponen los totales de la facción del usuario.
"""

from datetime import datetime, time, timezone

from sqlalchemy.orm import Session

from app.models.battle_royale import BattleRoyaleEvent, BrEventStatus, BrSeal, Champion, Duel
from app.models.faction import Faction
from app.models.season import Season
from app.models.user import User
from app.schemas.battle_royale import (
    BrStateOut,
    ChampionOut,
    CurrentDuelOut,
    FactionRoundOut,
    RoundResultOut,
    SealOptionOut,
    SealStateOut,
    TacticTotalsOut,
    WinnerOut,
    ZoneOut,
)
from app.services.battle_royale.resolution import MAX_WOUNDS, is_alive
from app.services.battle_royale.rounds import current_duel
from app.services.battle_royale.seals import SEAL_BONUSES, seal_is_overdue, winning_champion_user_id
from app.services.battle_royale.voting import faction_has_alive_champion, faction_totals, find_vote
from app.services.battle_royale.zones import ARENA, TOTAL_ROUNDS, ZONE_IDS, ZONE_NAMES
from app.services.season import get_active_season


def displayed_event(db: Session) -> tuple[BattleRoyaleEvent | None, Season | None]:
    try:
        season = get_active_season(db)
    except ValueError:
        return None, None
    event = db.query(BattleRoyaleEvent).filter(BattleRoyaleEvent.season_id == season.id).first()
    if event is None:
        event = db.query(BattleRoyaleEvent).filter(BattleRoyaleEvent.next_season_id == season.id).first()
    if event is None:
        return None, season
    return event, db.get(Season, event.season_id)


def _zones(fallen: list[str]) -> list[ZoneOut]:
    return [
        ZoneOut(
            id=zone,
            name=ZONE_NAMES[zone],
            fallen=zone in fallen,
            fall_order=fallen.index(zone) + 1 if zone in fallen else None,
            is_arena=zone == ARENA,
        )
        for zone in ZONE_IDS
    ]


def _champions(db: Session, event: BattleRoyaleEvent) -> list[ChampionOut]:
    rows = (
        db.query(Champion, Faction, User)
        .join(Faction, Faction.id == Champion.faction_id)
        .join(User, User.id == Champion.user_id)
        .filter(Champion.event_id == event.id)
        .order_by(Faction.slug.asc())
        .all()
    )
    return [
        ChampionOut(
            champion_id=champion.id,
            faction_slug=faction.slug,
            faction_name=faction.name,
            faction_color=faction.color,
            user_id=user.id,
            handle=user.handle,
            wounds=champion.wounds,
            max_wounds=MAX_WOUNDS,
            alive=is_alive(champion.wounds),
            eliminated_round=champion.eliminated_round,
            total_score=champion.total_score,
        )
        for champion, faction, user in rows
    ]


def _current_duel(db: Session, event: BattleRoyaleEvent, viewer: User) -> CurrentDuelOut | None:
    if event.status != BrEventStatus.active:
        return None
    duel = current_duel(db, event)
    if duel is None or duel.is_resolved:
        return None
    vote = find_vote(db, duel.id, viewer.id)
    eligible = faction_has_alive_champion(db, event.id, viewer.faction_id)
    totals = faction_totals(db, duel.id, viewer.faction_id) if viewer.faction_id else None
    return CurrentDuelOut(
        id=duel.id,
        round_number=duel.round_number,
        zone=duel.zone,
        zone_name=ZONE_NAMES[duel.zone],
        resolves_on=duel.resolves_on,
        closes_at=datetime.combine(duel.resolves_on, time(23, 59), tzinfo=timezone.utc),
        can_vote=eligible and vote is None,
        has_voted=vote is not None,
        my_tactic=vote.tactic if vote else None,
        my_weight=vote.weight if vote else None,
        my_faction_totals=TacticTotalsOut(**totals.weights) if totals else None,
        my_faction_voters=totals.voters if totals else 0,
    )


def _eliminated_slug(db: Session, duel: Duel) -> str | None:
    if duel.wounded_champion_id is None:
        return None
    champion = db.get(Champion, duel.wounded_champion_id)
    if champion is None or champion.eliminated_round != duel.round_number:
        return None
    return duel.result.get("wounded") if duel.result else None


def _last_round(db: Session, event: BattleRoyaleEvent) -> RoundResultOut | None:
    duel = (
        db.query(Duel)
        .filter(Duel.event_id == event.id, Duel.resolved_at.is_not(None))
        .order_by(Duel.round_number.desc())
        .first()
    )
    if duel is None or duel.resolved_at is None:
        return None
    result = duel.result or {}
    return RoundResultOut(
        duel_id=duel.id,
        round_number=duel.round_number,
        zone=duel.zone,
        zone_name=ZONE_NAMES[duel.zone],
        resolved_at=duel.resolved_at,
        wounded_faction_slug=result.get("wounded"),
        reason=result.get("reason", "below_gap" if result.get("wounded") else "within_gap"),
        eliminated_faction_slug=_eliminated_slug(db, duel),
        factions=[FactionRoundOut(**item) for item in result.get("factions", [])],
    )


def _winner(db: Session, event: BattleRoyaleEvent) -> WinnerOut | None:
    if event.winner_faction_id is None:
        return None
    faction = db.get(Faction, event.winner_faction_id)
    user_id = winning_champion_user_id(db, event)
    user = db.get(User, user_id) if user_id else None
    return WinnerOut(
        faction_slug=faction.slug,
        faction_name=faction.name,
        champion_user_id=user.id if user else None,
        champion_handle=user.handle if user else None,
    )


def can_choose_seal(db: Session, event: BattleRoyaleEvent, viewer: User, now: datetime) -> bool:
    if event.status != BrEventStatus.finished:
        return False
    if viewer.is_admin:
        return True
    in_time = event.seal_deadline is None or not seal_is_overdue(event.seal_deadline, now)
    return in_time and winning_champion_user_id(db, event) == viewer.id


def _seal_state(db: Session, event: BattleRoyaleEvent | None, viewer: User, now: datetime) -> SealStateOut:
    options = [
        SealOptionOut(id=BrSeal(seal), stat=next(iter(bonus)), bonus=next(iter(bonus.values())))
        for seal, bonus in SEAL_BONUSES.items()
    ]
    if event is None:
        return SealStateOut(options=options, selected=None, deadline=None, can_choose=False)
    return SealStateOut(
        options=options,
        selected=event.seal,
        deadline=event.seal_deadline,
        can_choose=can_choose_seal(db, event, viewer, now),
    )


def _next_season_number(db: Session, event: BattleRoyaleEvent) -> int | None:
    if event.next_season_id is None:
        return None
    season = db.get(Season, event.next_season_id)
    return season.number if season else None


def build_state(db: Session, viewer: User, now: datetime | None = None) -> BrStateOut:
    now = now or datetime.now(timezone.utc)
    event, season = displayed_event(db)
    if event is None:
        return BrStateOut(
            status="none",
            season_id=season.id if season else None,
            season_number=season.number if season else None,
            total_rounds=TOTAL_ROUNDS,
            zones=_zones([]),
            seal=_seal_state(db, None, viewer, now),
        )
    duel = _current_duel(db, event, viewer)
    return BrStateOut(
        status=event.status.value,
        event_id=event.id,
        season_id=event.season_id,
        season_number=season.number if season else None,
        next_season_number=_next_season_number(db, event),
        started_at=event.started_at,
        finished_at=event.finished_at,
        round_number=event.round_number,
        total_rounds=TOTAL_ROUNDS,
        current_zone=duel.zone if duel else None,
        fallen_zones=list(event.fallen_zones),
        zones=_zones(list(event.fallen_zones)),
        champions=_champions(db, event),
        current_duel=duel,
        last_round=_last_round(db, event),
        winner=_winner(db, event),
        seal=_seal_state(db, event, viewer, now),
    )
