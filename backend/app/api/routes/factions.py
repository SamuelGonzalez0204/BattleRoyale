from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.rate_limit import limiter, user_or_ip_key
from app.db.session import get_db
from app.models.user import User
from app.schemas.faction import FactionMemberOut, FactionOut
from app.services.faction_directory import NoFaction, faction_members, faction_summaries
from app.services.season import find_active_season

router = APIRouter(prefix="/api/factions", tags=["factions"])

MEMBERS_DEFAULT_LIMIT = 20
MEMBERS_MAX_LIMIT = 50
HANDLE_MAX_LENGTH = 60


@router.get("", response_model=list[FactionOut])
def list_factions(db: Session = Depends(get_db)) -> list[FactionOut]:
    return [FactionOut(**asdict(summary)) for summary in faction_summaries(db)]


@router.get("/me/members", response_model=list[FactionMemberOut])
@limiter.limit(get_settings().rate_limit_public_read, key_func=user_or_ip_key)
def list_my_faction_members(
    request: Request,
    q: str | None = Query(None, max_length=HANDLE_MAX_LENGTH),
    limit: int = Query(MEMBERS_DEFAULT_LIMIT, ge=1, le=MEMBERS_MAX_LIMIT),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[FactionMemberOut]:
    """Miembros de mi facción (sin mí) con lo patrocinado esta temporada. 403 sin facción."""
    try:
        members = faction_members(db, current_user, find_active_season(db), q, limit)
    except NoFaction as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return [FactionMemberOut(**asdict(member)) for member in members]
