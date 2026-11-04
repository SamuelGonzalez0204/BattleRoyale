"""Panel de admin. Todas las rutas exigen `require_admin` (401 sin sesión, 403 sin permiso)."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.api.routes.decisions import decision_out
from app.core.config import get_settings
from app.core.rate_limit import limiter, user_or_ip_key
from app.db.session import get_db
from app.models.report import ReportStatus
from app.models.season import Season
from app.models.user import HandleVerificationStatus, User
from app.schemas.admin import (
    EmergencyDecisionIn,
    HandleRequestOut,
    HandleReviewIn,
    ReportAdminOut,
    ReportModerationIn,
    SeasonAdminOut,
)
from app.schemas.decision import DecisionOut
from app.services import moderation
from app.services.daily_decision import DecisionHasVotes, EmergencyDecision, set_emergency_decision
from app.services.season import FinalPhaseReached, following_phase, force_advance_phase, get_active_season

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])

ADMIN_LIMIT = get_settings().rate_limit_admin


def _season_out(season: Season) -> SeasonAdminOut:
    upcoming = following_phase(season.phase)
    return SeasonAdminOut(
        id=season.id,
        number=season.number,
        name=season.name,
        phase=season.phase.value,
        next_phase=upcoming.value if upcoming else None,
        is_active=season.is_active,
        started_at=season.started_at,
        phase_started_at=season.phase_started_at,
        ended_at=season.ended_at,
    )


def _handle_out(user: User) -> HandleRequestOut:
    return HandleRequestOut(
        user_id=user.id,
        handle=user.handle,
        email=user.email,
        status=user.handle_verification_status.value,
        code=user.handle_verification_code,
        requested_at=user.handle_verification_requested_at,
        reviewed_at=user.handle_verification_reviewed_at,
    )


def _report_out(row: moderation.ReportRow) -> ReportAdminOut:
    report, reporter_handle, reported_handle = row
    return ReportAdminOut(
        id=report.id,
        reporter_id=report.reporter_id,
        reporter_handle=reporter_handle,
        reported_user_id=report.reported_user_id,
        reported_handle=reported_handle,
        reason=report.reason,
        details=report.details,
        status=report.status,
        created_at=report.created_at,
    )


def _conflict(exc: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


def _not_found(exc: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Temporadas --------------------------------------------------------------


@router.get("/seasons", response_model=list[SeasonAdminOut])
@limiter.limit(ADMIN_LIMIT, key_func=user_or_ip_key)
def list_seasons(request: Request, db: Session = Depends(get_db)) -> list[SeasonAdminOut]:
    seasons = db.query(Season).order_by(Season.number.desc()).all()
    return [_season_out(season) for season in seasons]


@router.post("/seasons/{season_id}/advance-phase", response_model=SeasonAdminOut)
@limiter.limit(ADMIN_LIMIT, key_func=user_or_ip_key)
def advance_season_phase(request: Request, season_id: uuid.UUID, db: Session = Depends(get_db)) -> SeasonAdminOut:
    season = db.query(Season).filter(Season.id == season_id).with_for_update().first()
    if season is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Esa temporada no existe")
    try:
        force_advance_phase(season, datetime.now(timezone.utc))
    except FinalPhaseReached as exc:
        db.rollback()
        raise _conflict(exc) from exc
    db.commit()
    return _season_out(season)


# --- Decisión de emergencia --------------------------------------------------


@router.post("/decisions/emergency", response_model=DecisionOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(ADMIN_LIMIT, key_func=user_or_ip_key)
def emergency_decision(request: Request, payload: EmergencyDecisionIn, db: Session = Depends(get_db)) -> DecisionOut:
    try:
        season = get_active_season(db)
    except ValueError as exc:
        raise _conflict(exc) from exc
    content = EmergencyDecision(**payload.model_dump())
    try:
        decision = set_emergency_decision(db, season, content)
    except DecisionHasVotes as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La decisión de hoy ya tiene votos: no se puede reemplazar",
        ) from exc
    return decision_out(db, decision, my_vote=None)


# --- Reports -----------------------------------------------------------------


@router.get("/reports", response_model=list[ReportAdminOut])
@limiter.limit(ADMIN_LIMIT, key_func=user_or_ip_key)
def list_reports(
    request: Request,
    report_status: ReportStatus = Query(ReportStatus.open, alias="status"),
    db: Session = Depends(get_db),
) -> list[ReportAdminOut]:
    return [_report_out(row) for row in moderation.list_reports(db, report_status)]


@router.post("/reports/{report_id}", response_model=ReportAdminOut)
@limiter.limit(ADMIN_LIMIT, key_func=user_or_ip_key)
def moderate_report(
    request: Request,
    report_id: uuid.UUID,
    payload: ReportModerationIn,
    db: Session = Depends(get_db),
) -> ReportAdminOut:
    try:
        moderation.moderate_report(db, report_id, ReportStatus(payload.status))
    except moderation.NotFound as exc:
        raise _not_found(exc) from exc
    except moderation.AlreadyModerated as exc:
        db.rollback()
        raise _conflict(exc) from exc
    return _report_out(moderation.get_report_row(db, report_id))


# --- Handles -----------------------------------------------------------------


@router.get("/handles", response_model=list[HandleRequestOut])
@limiter.limit(ADMIN_LIMIT, key_func=user_or_ip_key)
def list_handle_requests(
    request: Request,
    handle_status: HandleVerificationStatus = Query(HandleVerificationStatus.pending, alias="status"),
    db: Session = Depends(get_db),
) -> list[HandleRequestOut]:
    return [_handle_out(user) for user in moderation.list_handle_requests(db, handle_status)]


@router.post("/handles/{user_id}", response_model=HandleRequestOut)
@limiter.limit(ADMIN_LIMIT, key_func=user_or_ip_key)
def review_handle(
    request: Request,
    user_id: uuid.UUID,
    payload: HandleReviewIn,
    db: Session = Depends(get_db),
) -> HandleRequestOut:
    try:
        user = moderation.review_handle(db, user_id, HandleVerificationStatus(payload.decision))
    except moderation.NotFound as exc:
        raise _not_found(exc) from exc
    except moderation.AlreadyModerated as exc:
        db.rollback()
        raise _conflict(exc) from exc
    return _handle_out(user)
