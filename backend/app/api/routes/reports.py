from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.rate_limit import limiter, user_or_ip_key
from app.db.session import get_db
from app.models.report import Report, ReportStatus
from app.models.user import User
from app.schemas.report import ReportCreate, ReportOut

router = APIRouter(prefix="/api/reports", tags=["reports"])

DUPLICATE_REPORT = "Ya tienes un report abierto sobre esta cuenta"


def _has_open_report(db: Session, reporter: User, payload: ReportCreate) -> bool:
    return (
        db.query(Report.id)
        .filter(
            Report.reporter_id == reporter.id,
            Report.reported_user_id == payload.reported_user_id,
            Report.status == ReportStatus.open,
        )
        .first()
        is not None
    )


@router.post("", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(get_settings().rate_limit_reports, key_func=user_or_ip_key)
def create_report(
    request: Request,
    payload: ReportCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportOut:
    if payload.reported_user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No puedes reportarte a ti mismo")
    if db.get(User, payload.reported_user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Esa cuenta no existe")
    if _has_open_report(db, current_user, payload):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICATE_REPORT)

    report = Report(
        reporter_id=current_user.id,
        reported_user_id=payload.reported_user_id,
        reason=payload.reason,
        details=payload.details,
    )
    db.add(report)
    try:
        db.commit()
    except IntegrityError as exc:
        # Carrera con otra petición idéntica: el índice único parcial manda.
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICATE_REPORT) from exc
    db.refresh(report)
    return ReportOut.model_validate(report)
