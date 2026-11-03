import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DecisionOut(BaseModel):
    id: uuid.UUID
    question: str
    option_a: str
    option_b: str
    closes_at: datetime
    votes_a: int
    votes_b: int
    my_vote: str | None = None
    # Campos añadidos en la Fase A (opcionales para no romper clientes existentes)
    effects_a: dict[str, int] = Field(default_factory=dict)
    effects_b: dict[str, int] = Field(default_factory=dict)
    role_affinity: str | None = None
    closed: bool = False
    winner: str | None = None


class VoteIn(BaseModel):
    option: str = Field(pattern="^[ab]$")
    chispas_to_spend: int = Field(default=0, ge=0, le=50)
