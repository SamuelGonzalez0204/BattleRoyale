from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.faction import Faction
from app.schemas.faction import FactionOut
from app.services.sorting import faction_counts

router = APIRouter(prefix="/api/factions", tags=["factions"])


@router.get("", response_model=list[FactionOut])
def list_factions(db: Session = Depends(get_db)) -> list[FactionOut]:
    factions = db.query(Faction).order_by(Faction.slug).all()
    counts = faction_counts(db)
    total = sum(counts.values()) or 1

    return [
        FactionOut(
            id=f.id,
            slug=f.slug,
            name=f.name,
            color=f.color,
            members=counts.get(str(f.id), 0),
            influence_pct=round(100 * counts.get(str(f.id), 0) / total, 1),
        )
        for f in factions
    ]
