"""Patrocinio (Fase B): gastar Chispas en un miembro de tu facción."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.rate_limit import limiter, user_or_ip_key
from app.db.session import get_db
from app.models.season import Season
from app.models.sponsorship import Sponsorship
from app.models.user import User
from app.schemas.sponsorship import (
    FactionSponsorBoardOut,
    SponsoredMemberOut,
    SponsorIn,
    SponsorLeaderboardOut,
    SponsorOut,
)
from app.services import sponsorship
from app.services.battle_royale.lifecycle import event_for_season
from app.services.economy import InsufficientChispas
from app.services.season import get_active_season

router = APIRouter(prefix="/api/sponsor", tags=["sponsor"])

ERROR_CODES: dict[type[Exception], int] = {
    sponsorship.SponsorClosed: status.HTTP_409_CONFLICT,
    sponsorship.SponsorForbidden: status.HTTP_403_FORBIDDEN,
    sponsorship.SponsorInvalid: status.HTTP_400_BAD_REQUEST,
    sponsorship.RecipientNotFound: status.HTTP_404_NOT_FOUND,
    InsufficientChispas: status.HTTP_400_BAD_REQUEST,
}


def _active_season(db: Session) -> Season:
    try:
        return get_active_season(db)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


def _recipient_total(db: Session, season: Season, recipient_id) -> int:
    total = (
        db.query(func.coalesce(func.sum(Sponsorship.chispas), 0))
        .filter(Sponsorship.season_id == season.id, Sponsorship.recipient_id == recipient_id)
        .scalar()
    )
    return int(total or 0)


@router.post("", response_model=SponsorOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(get_settings().rate_limit_battle_royale, key_func=user_or_ip_key)
def sponsor(
    request: Request,
    payload: SponsorIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SponsorOut:
    season = _active_season(db)
    try:
        created = sponsorship.sponsor_member(
            db, season, current_user, payload.user_id, payload.chispas, datetime.now(timezone.utc)
        )
    except tuple(ERROR_CODES) as exc:
        raise HTTPException(status_code=ERROR_CODES[type(exc)], detail=str(exc)) from exc
    recipient = db.get(User, created.recipient_id)
    return SponsorOut(
        id=created.id,
        recipient_id=created.recipient_id,
        recipient_handle=recipient.handle,
        chispas=created.chispas,
        my_chispas=current_user.chispas,
        recipient_total=_recipient_total(db, season, created.recipient_id),
        created_at=created.created_at,
    )


@router.get("/leaderboard", response_model=SponsorLeaderboardOut)
def leaderboard(
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SponsorLeaderboardOut:
    season = _active_season(db)
    boards = sponsorship.sponsor_leaderboard(db, season, limit)
    return SponsorLeaderboardOut(
        season_id=season.id,
        season_number=season.number,
        open=sponsorship.sponsoring_is_open(season.phase, event_for_season(db, season) is not None),
        factions=[
            FactionSponsorBoardOut(
                faction_slug=board.faction_slug,
                faction_name=board.faction_name,
                members=[SponsoredMemberOut(**member.__dict__) for member in board.members],
            )
            for board in boards
        ],
    )
