from datetime import date

from pydantic import BaseModel

from app.schemas.faction import FactionOut


class LoreSeasonOut(BaseModel):
    number: int
    name: str
    phase: str


class LoreDecisionOut(BaseModel):
    date: date
    season_number: int
    question: str
    region: str | None
    region_name: str | None
    winner: str | None
    winner_option: str | None
    effects_applied: dict[str, int]


class LoreBattleRoyaleOut(BaseModel):
    season_number: int
    winner_faction_slug: str | None
    winner_faction_name: str | None
    champion_handle: str | None
    seal: str | None


class LoreOut(BaseModel):
    season: LoreSeasonOut | None
    world: dict[str, int] | None
    factions: list[FactionOut]
    decisions: list[LoreDecisionOut]
    battle_royales: list[LoreBattleRoyaleOut]
