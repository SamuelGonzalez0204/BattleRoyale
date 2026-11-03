import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.report import REPORT_DETAILS_MAX_LENGTH, ReportReason, ReportStatus


class ReportCreate(BaseModel):
    reported_user_id: uuid.UUID
    reason: ReportReason
    details: str | None = Field(default=None, max_length=REPORT_DETAILS_MAX_LENGTH)


class ReportOut(BaseModel):
    id: uuid.UUID
    reported_user_id: uuid.UUID
    reason: ReportReason
    details: str | None
    status: ReportStatus
    created_at: datetime

    model_config = {"from_attributes": True}
