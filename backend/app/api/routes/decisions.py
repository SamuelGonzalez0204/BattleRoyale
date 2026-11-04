from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.decision import Decision, Vote
from app.models.user import User
from app.schemas.decision import DecisionOut, VoteIn
from app.services.daily_decision import ensure_decision_for_today, vote_tallies
from app.services.economy import InsufficientChispas, spend_chispas
from app.services.season import get_active_season

router = APIRouter(prefix="/api/decisions", tags=["decisions"])


def _today_decision(db: Session) -> Decision:
    season = get_active_season(db)
    try:
        return ensure_decision_for_today(db, season)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


def decision_out(db: Session, decision: Decision, my_vote: str | None) -> DecisionOut:
    votes_a, votes_b = vote_tallies(db, decision.id)
    return DecisionOut(
        id=decision.id,
        question=decision.question,
        option_a=decision.option_a,
        option_b=decision.option_b,
        closes_at=decision.closes_at,
        votes_a=votes_a,
        votes_b=votes_b,
        my_vote=my_vote,
        effects_a=decision.effects_a or {},
        effects_b=decision.effects_b or {},
        role_affinity=decision.role_affinity.value if decision.role_affinity else None,
        closed=decision.is_closed,
        winner=decision.winner,
    )


@router.get("/today", response_model=DecisionOut)
def read_today(
    db: Session = Depends(get_db),
    # get_current_user nunca devuelve None: sin token válido responde 401.
    current_user: User = Depends(get_current_user),
) -> DecisionOut:
    decision = _today_decision(db)

    my_vote = None
    existing = db.query(Vote).filter(Vote.decision_id == decision.id, Vote.user_id == current_user.id).first()
    if existing:
        my_vote = existing.option

    return decision_out(db, decision, my_vote)


@router.post("/today/vote", response_model=DecisionOut)
def vote_today(
    payload: VoteIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DecisionOut:
    decision = _today_decision(db)

    if decision.is_closed or decision.closes_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La decisión de hoy ya cerró")

    existing = db.query(Vote).filter(Vote.decision_id == decision.id, Vote.user_id == current_user.id).first()
    weight = 1 + payload.chispas_to_spend

    if payload.chispas_to_spend > 0:
        try:
            spend_chispas(db, current_user, payload.chispas_to_spend, reason="voto_peso_extra")
        except InsufficientChispas as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if existing:
        existing.option = payload.option
        existing.weight = weight
    else:
        db.add(Vote(decision_id=decision.id, user_id=current_user.id, option=payload.option, weight=weight))

    db.commit()

    return decision_out(db, decision, payload.option)
