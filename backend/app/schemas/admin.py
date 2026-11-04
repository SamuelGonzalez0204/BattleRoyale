import uuid
from collections.abc import Mapping
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.report import ReportReason, ReportStatus
from app.models.user import UserRole
from app.services.world_effects import validate_effects


class SeasonAdminOut(BaseModel):
    id: uuid.UUID
    number: int
    name: str
    phase: str
    next_phase: str | None
    is_active: bool
    started_at: datetime
    phase_started_at: datetime
    ended_at: datetime | None


class EmergencyDecisionIn(BaseModel):
    question: str = Field(min_length=1, max_length=280)
    option_a: str = Field(min_length=1, max_length=120)
    option_b: str = Field(min_length=1, max_length=120)
    effects_a: dict[str, int] = Field(default_factory=dict)
    effects_b: dict[str, int] = Field(default_factory=dict)
    role_affinity: UserRole | None = None

    @field_validator("effects_a", "effects_b", mode="before")
    @classmethod
    def _known_stats_with_integer_deltas(cls, value: object) -> object:
        # Misma regla que aplica el cierre diario (world_effects), antes de que
        # Pydantic convierta "3" o True en enteros.
        if isinstance(value, Mapping):
            validate_effects(value)
        return value


class ReportAdminOut(BaseModel):
    id: uuid.UUID
    reporter_id: uuid.UUID
    reporter_handle: str
    reported_user_id: uuid.UUID
    reported_handle: str
    reason: ReportReason
    details: str | None
    status: ReportStatus
    created_at: datetime


class ReportModerationIn(BaseModel):
    status: Literal["reviewed", "dismissed"]


class HandleRequestOut(BaseModel):
    user_id: uuid.UUID
    handle: str
    email: str
    status: str
    code: str | None
    requested_at: datetime | None
    reviewed_at: datetime | None


class HandleReviewIn(BaseModel):
    decision: Literal["verified", "rejected"]
