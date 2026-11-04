import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SponsorIn(BaseModel):
    user_id: uuid.UUID
    chispas: int = Field(ge=1, le=1000)


class SponsorOut(BaseModel):
    id: uuid.UUID
    recipient_id: uuid.UUID
    recipient_handle: str
    chispas: int
    my_chispas: int
    recipient_total: int  # total patrocinado al destinatario esta temporada
    created_at: datetime


class SponsoredMemberOut(BaseModel):
    user_id: uuid.UUID
    handle: str
    total_chispas: int
    sponsorships: int


class FactionSponsorBoardOut(BaseModel):
    faction_slug: str
    faction_name: str
    members: list[SponsoredMemberOut]


class SponsorLeaderboardOut(BaseModel):
    season_id: uuid.UUID
    season_number: int
    open: bool  # ¿se puede patrocinar ahora mismo?
    factions: list[FactionSponsorBoardOut]
