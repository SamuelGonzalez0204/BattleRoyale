"""La Última Luz (Fase B): estado, votos de táctica y sello. Todas exigen sesión."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.rate_limit import limiter, user_or_ip_key
from app.db.session import get_db
from app.models.season import Season
from app.models.user import User
from app.schemas.battle_royale import (
    BrStateOut,
    SealIn,
    SealOut,
    SeasonSummaryOut,
    TacticTotalsOut,
    TacticVoteIn,
    TacticVoteOut,
)
from app.services.battle_royale import voting
from app.services.battle_royale.seals import SealForbidden, SealNotAvailable, apply_seal
from app.services.battle_royale.state import build_state, displayed_event
from app.services.economy import InsufficientChispas
from app.services.season import get_world_state, world_stats

router = APIRouter(prefix="/api/br", tags=["battle-royale"])

BR_LIMIT = get_settings().rate_limit_battle_royale


def _error(code: int, exc: Exception) -> HTTPException:
    return HTTPException(status_code=code, detail=str(exc))


@router.get("/state", response_model=BrStateOut)
def read_state(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> BrStateOut:
    return build_state(db, current_user)


@router.post("/duels/{duel_id}/vote", response_model=TacticVoteOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(BR_LIMIT, key_func=user_or_ip_key)
def vote_duel(
    request: Request,
    duel_id: uuid.UUID,
    payload: TacticVoteIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TacticVoteOut:
    try:
        vote = voting.cast_tactic_vote(db, duel_id, current_user, payload.tactic, payload.chispas_to_spend)
    except voting.DuelNotFound as exc:
        raise _error(status.HTTP_404_NOT_FOUND, exc) from exc
    except voting.NotEligible as exc:
        raise _error(status.HTTP_403_FORBIDDEN, exc) from exc
    except (voting.DuelClosed, voting.AlreadyVoted) as exc:
        raise _error(status.HTTP_409_CONFLICT, exc) from exc
    except InsufficientChispas as exc:
        raise _error(status.HTTP_400_BAD_REQUEST, exc) from exc
    totals = voting.faction_totals(db, vote.duel_id, vote.faction_id)
    return TacticVoteOut(
        duel_id=vote.duel_id,
        tactic=vote.tactic,
        chispas_spent=vote.chispas_spent,
        weight=vote.weight,
        my_chispas=current_user.chispas,
        my_faction_totals=TacticTotalsOut(**totals.weights),
        my_faction_voters=totals.voters,
    )


@router.post("/seal", response_model=SealOut)
@limiter.limit(BR_LIMIT, key_func=user_or_ip_key)
def choose_seal(
    request: Request,
    payload: SealIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SealOut:
    event, season = displayed_event(db)
    if event is None or season is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No hay ninguna Última Luz")
    previous_number = season.number
    try:
        new_season: Season = apply_seal(db, event.id, payload.seal, datetime.now(timezone.utc), current_user)
    except SealNotAvailable as exc:
        raise _error(status.HTTP_409_CONFLICT, exc) from exc
    except SealForbidden as exc:
        raise _error(status.HTTP_403_FORBIDDEN, exc) from exc
    return SealOut(
        seal=payload.seal,
        previous_season_number=previous_number,
        new_season=SeasonSummaryOut(
            id=new_season.id, number=new_season.number, name=new_season.name, phase=new_season.phase.value
        ),
        world=world_stats(get_world_state(db, new_season)),
    )
