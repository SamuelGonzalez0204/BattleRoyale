from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.faction import FactionOut
from app.services.economy import award_chispas
from app.services.sorting import assign_faction, faction_counts

router = APIRouter(prefix="/api/augurio", tags=["augurio"])


@router.post("/assign", response_model=FactionOut)
def assign(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FactionOut:
    if current_user.faction_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El Augurio ya decidió tu facción para esta temporada",
        )

    faction = assign_faction(db)
    current_user.faction_id = faction.id
    award_chispas(db, current_user, amount=10, reason="augurio_bienvenida")
    db.commit()

    counts = faction_counts(db)
    total = sum(counts.values()) or 1
    members = counts.get(str(faction.id), 0)
    return FactionOut(
        id=faction.id,
        slug=faction.slug,
        name=faction.name,
        color=faction.color,
        members=members,
        influence_pct=round(100 * members / total, 1),
    )
