"""Lore (Fase E3): vista pública combinada para la wiki.

Temporada actual, stats del mundo, facciones, últimas decisiones cerradas y
resultados de Últimas Luces pasadas. Consultas fijas, sin N+1.
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import and_
from sqlalchemy.orm import Session, aliased

from app.data.regions import region_name
from app.models.battle_royale import BattleRoyaleEvent, Champion
from app.models.decision import Decision
from app.models.faction import Faction
from app.models.season import Season
from app.models.user import User
from app.models.world import WorldState
from app.services.faction_directory import FactionSummary, faction_summaries
from app.services.season import find_active_season, world_stats

RECENT_DECISIONS = 30


@dataclass(frozen=True)
class SeasonInfo:
    number: int
    name: str
    phase: str


@dataclass(frozen=True)
class ClosedDecision:
    date: date
    season_number: int
    question: str
    region: str | None
    region_name: str | None
    winner: str | None
    winner_option: str | None
    effects_applied: dict[str, int]


@dataclass(frozen=True)
class BattleRoyaleResult:
    season_number: int
    winner_faction_slug: str | None
    winner_faction_name: str | None
    champion_handle: str | None
    seal: str | None


@dataclass(frozen=True)
class Lore:
    season: SeasonInfo | None
    world: dict[str, int] | None
    factions: list[FactionSummary]
    decisions: list[ClosedDecision]
    battle_royales: list[BattleRoyaleResult]


def _world(db: Session, season: Season | None) -> dict[str, int] | None:
    if season is None:
        return None
    state = db.query(WorldState).filter(WorldState.season_id == season.id).first()
    return world_stats(state) if state else None


def _closed_decision(decision: Decision, season_number: int) -> ClosedDecision:
    winner = decision.winner
    options = {"a": (decision.option_a, decision.effects_a), "b": (decision.option_b, decision.effects_b)}
    option, effects = options.get(winner or "", (None, {}))
    return ClosedDecision(
        date=decision.day,
        season_number=season_number,
        question=decision.question,
        region=decision.region,
        region_name=region_name(decision.region),
        winner=winner,
        winner_option=option,
        effects_applied=dict(effects or {}),
    )


def recent_closed_decisions(db: Session, limit: int = RECENT_DECISIONS) -> list[ClosedDecision]:
    rows = (
        db.query(Decision, Season.number)
        .join(Season, Season.id == Decision.season_id)
        .filter(Decision.closed_at.is_not(None))
        .order_by(Decision.day.desc(), Decision.closed_at.desc())
        .limit(limit)
        .all()
    )
    return [_closed_decision(decision, number) for decision, number in rows]


def battle_royale_results(db: Session) -> list[BattleRoyaleResult]:
    """Últimas Luces con ganador (terminadas o selladas), de la más reciente a la más antigua."""
    winner = aliased(Faction)
    rows = (
        db.query(Season.number, winner.slug, winner.name, User.handle, BattleRoyaleEvent.seal)
        .join(Season, Season.id == BattleRoyaleEvent.season_id)
        .outerjoin(winner, winner.id == BattleRoyaleEvent.winner_faction_id)
        .outerjoin(
            Champion,
            and_(
                Champion.event_id == BattleRoyaleEvent.id,
                Champion.faction_id == BattleRoyaleEvent.winner_faction_id,
            ),
        )
        .outerjoin(User, User.id == Champion.user_id)
        .filter(BattleRoyaleEvent.winner_faction_id.is_not(None))
        .order_by(Season.number.desc())
        .all()
    )
    return [
        BattleRoyaleResult(
            season_number=number,
            winner_faction_slug=slug,
            winner_faction_name=name,
            champion_handle=handle,
            seal=seal.value if seal else None,
        )
        for number, slug, name, handle, seal in rows
    ]


def build_lore(db: Session) -> Lore:
    season = find_active_season(db)
    info = SeasonInfo(number=season.number, name=season.name, phase=season.phase.value) if season else None
    return Lore(
        season=info,
        world=_world(db, season),
        factions=faction_summaries(db),
        decisions=recent_closed_decisions(db),
        battle_royales=battle_royale_results(db),
    )
