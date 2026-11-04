import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

REPORT_DETAILS_MAX_LENGTH = 500


class ReportReason(str, enum.Enum):
    bot = "bot"
    suplantacion = "suplantacion"
    abuso = "abuso"
    otro = "otro"


class ReportStatus(str, enum.Enum):
    open = "open"
    reviewed = "reviewed"
    dismissed = "dismissed"


class Report(Base):
    """Denuncia de una cuenta por otra. La moderación (reviewed/dismissed) llega en D4."""

    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint("reporter_id <> reported_user_id", name="ck_report_not_self"),
        # Un solo report abierto por pareja denunciante → denunciado.
        Index(
            "uq_reports_open_pair",
            "reporter_id",
            "reported_user_id",
            unique=True,
            postgresql_where=text("status = 'open'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reporter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reported_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    reason: Mapped[ReportReason] = mapped_column(Enum(ReportReason, name="report_reason"), nullable=False)
    details: Mapped[str | None] = mapped_column(String(REPORT_DETAILS_MAX_LENGTH), nullable=True)
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="report_status"),
        default=ReportStatus.open,
        server_default=ReportStatus.open.value,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
