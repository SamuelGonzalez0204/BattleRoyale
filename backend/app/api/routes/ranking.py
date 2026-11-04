"""Ranking (Fase E2). Exige sesión; `me` es el puesto de quien consulta."""

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.rate_limit import limiter, user_or_ip_key
from app.db.session import get_db
from app.models.user import User
from app.schemas.ranking import MyRankOut, RankingItemOut, RankingOut
from app.services.ranking import RankingScope, UnknownFaction, ranking_page
from app.services.season import find_active_season

router = APIRouter(prefix="/api/ranking", tags=["ranking"])

DEFAULT_LIMIT = 20
MAX_LIMIT = 50


@router.get("", response_model=RankingOut)
@limiter.limit(get_settings().rate_limit_public_read, key_func=user_or_ip_key)
def read_ranking(
    request: Request,
    scope: RankingScope = Query(RankingScope.chispas),
    faction: str | None = Query(None, max_length=32),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RankingOut:
    try:
        page = ranking_page(
            db,
            scope=scope,
            season=find_active_season(db),
            faction_slug=faction,
            limit=limit,
            offset=offset,
            me_id=current_user.id,
        )
    except (UnknownFaction, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return RankingOut(
        items=[RankingItemOut(**asdict(item)) for item in page.items],
        total=page.total,
        limit=limit,
        offset=offset,
        me=MyRankOut(**asdict(page.me)) if page.me else None,
    )
