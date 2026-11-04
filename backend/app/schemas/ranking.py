import uuid

from pydantic import BaseModel


class RankingItemOut(BaseModel):
    rank: int
    user_id: uuid.UUID
    handle: str
    faction_slug: str | None
    role: str | None
    value: int


class MyRankOut(BaseModel):
    rank: int
    value: int


class RankingOut(BaseModel):
    items: list[RankingItemOut]
    total: int
    limit: int
    offset: int
    me: MyRankOut | None
