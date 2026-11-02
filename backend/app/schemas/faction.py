import uuid

from pydantic import BaseModel


class FactionOut(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    color: str
    members: int
    influence_pct: float

    model_config = {"from_attributes": True}
