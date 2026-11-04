import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.battle_royale import BrSeal, BrTactic

BrStatus = Literal["none", "active", "finished", "sealed"]


class ZoneOut(BaseModel):
    id: str
    name: str
    fallen: bool
    fall_order: int | None  # 1..6 si ya cayó; None si sigue en pie
    is_arena: bool


class ChampionOut(BaseModel):
    champion_id: uuid.UUID
    faction_slug: str
    faction_name: str
    faction_color: str
    user_id: uuid.UUID
    handle: str
    wounds: int
    max_wounds: int
    alive: bool
    eliminated_round: int | None
    total_score: float


class TacticTotalsOut(BaseModel):
    ataque: int = 0
    defensa: int = 0
    astucia: int = 0


class CurrentDuelOut(BaseModel):
    id: uuid.UUID
    round_number: int
    zone: str
    zone_name: str
    resolves_on: date
    closes_at: datetime  # cierre diario de las 23:59 UTC de resolves_on
    can_vote: bool  # tengo facción con campeón vivo y aún no voté
    has_voted: bool
    my_tactic: BrTactic | None
    my_weight: int | None
    # Solo mi facción: las tácticas del resto no se revelan hasta resolver.
    my_faction_totals: TacticTotalsOut | None
    my_faction_voters: int


class FactionRoundOut(BaseModel):
    faction_slug: str
    tactic: BrTactic | None
    total_weight: int
    participation: float
    wins: int
    score: float
    wounded: bool


class RoundResultOut(BaseModel):
    duel_id: uuid.UUID
    round_number: int
    zone: str
    zone_name: str
    resolved_at: datetime
    wounded_faction_slug: str | None
    eliminated_faction_slug: str | None
    reason: str  # below_gap (hubo herida) | within_gap (nadie herido) | final_round | no_contenders
    factions: list[FactionRoundOut]


class WinnerOut(BaseModel):
    faction_slug: str
    faction_name: str
    champion_user_id: uuid.UUID | None
    champion_handle: str | None


class SealOptionOut(BaseModel):
    id: BrSeal
    stat: str
    bonus: int


class SealStateOut(BaseModel):
    options: list[SealOptionOut]
    selected: BrSeal | None
    deadline: datetime | None
    can_choose: bool  # soy el campeón ganador (en plazo) o admin, y falta el sello


class BrStateOut(BaseModel):
    status: BrStatus
    event_id: uuid.UUID | None = None
    season_id: uuid.UUID | None = None
    season_number: int | None = None
    next_season_number: int | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    round_number: int | None = None
    total_rounds: int
    current_zone: str | None = None
    fallen_zones: list[str] = Field(default_factory=list)
    zones: list[ZoneOut]
    champions: list[ChampionOut] = Field(default_factory=list)
    current_duel: CurrentDuelOut | None = None
    last_round: RoundResultOut | None = None
    winner: WinnerOut | None = None
    seal: SealStateOut


class TacticVoteIn(BaseModel):
    tactic: BrTactic
    chispas_to_spend: int = Field(default=0, ge=0, le=50)


class TacticVoteOut(BaseModel):
    duel_id: uuid.UUID
    tactic: BrTactic
    chispas_spent: int
    weight: int
    my_chispas: int
    my_faction_totals: TacticTotalsOut
    my_faction_voters: int


class SealIn(BaseModel):
    seal: BrSeal


class SeasonSummaryOut(BaseModel):
    id: uuid.UUID
    number: int
    name: str
    phase: str


class SealOut(BaseModel):
    seal: BrSeal
    previous_season_number: int
    new_season: SeasonSummaryOut
    world: dict[str, int]
