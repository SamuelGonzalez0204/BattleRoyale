"""Moderación desde el panel de admin: reports y verificación manual de handles."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Query, Session, aliased

from app.models.report import Report, ReportStatus
from app.models.user import HandleVerificationStatus, User

MODERATION_PAGE_SIZE = 200
REPORT_OUTCOMES = (ReportStatus.reviewed, ReportStatus.dismissed)
HANDLE_OUTCOMES = (HandleVerificationStatus.verified, HandleVerificationStatus.rejected)


class NotFound(LookupError):
    pass


class AlreadyModerated(Exception):
    """El elemento ya no está pendiente de revisión."""


ReportRow = tuple[Report, str, str]  # (report, handle_denunciante, handle_denunciado)


def _report_rows(db: Session) -> Query:
    reporter = aliased(User)
    reported = aliased(User)
    return (
        db.query(Report, reporter.handle, reported.handle)
        .join(reporter, Report.reporter_id == reporter.id)
        .join(reported, Report.reported_user_id == reported.id)
    )


def list_reports(db: Session, status: ReportStatus) -> list[ReportRow]:
    """Reports en `status` con los handles implicados, los más antiguos primero."""
    rows = (
        _report_rows(db)
        .filter(Report.status == status)
        .order_by(Report.created_at.asc())
        .limit(MODERATION_PAGE_SIZE)
        .all()
    )
    return [tuple(row) for row in rows]


def get_report_row(db: Session, report_id: uuid.UUID) -> ReportRow:
    row = _report_rows(db).filter(Report.id == report_id).first()
    if row is None:
        raise NotFound("Ese report no existe")
    return tuple(row)


def moderate_report(db: Session, report_id: uuid.UUID, outcome: ReportStatus) -> Report:
    if outcome not in REPORT_OUTCOMES:
        raise ValueError(f"Resultado de moderación no válido: {outcome!r}")
    report = db.query(Report).filter(Report.id == report_id).with_for_update().first()
    if report is None:
        raise NotFound("Ese report no existe")
    if report.status != ReportStatus.open:
        raise AlreadyModerated("Este report ya está moderado")
    report.status = outcome
    db.commit()
    return report


def list_handle_requests(db: Session, status: HandleVerificationStatus) -> list[User]:
    return (
        db.query(User)
        .filter(User.handle_verification_status == status)
        .order_by(User.handle_verification_requested_at.asc().nulls_last())
        .limit(MODERATION_PAGE_SIZE)
        .all()
    )


def review_handle(
    db: Session,
    user_id: uuid.UUID,
    outcome: HandleVerificationStatus,
    now: datetime | None = None,
) -> User:
    if outcome not in HANDLE_OUTCOMES:
        raise ValueError(f"Resultado de verificación no válido: {outcome!r}")
    user = db.query(User).filter(User.id == user_id).with_for_update().first()
    if user is None:
        raise NotFound("Esa cuenta no existe")
    if user.handle_verification_status != HandleVerificationStatus.pending:
        raise AlreadyModerated("Esa cuenta no tiene una verificación de handle pendiente")
    user.handle_verification_status = outcome
    user.handle_verification_reviewed_at = now or datetime.now(timezone.utc)
    db.commit()
    return user
