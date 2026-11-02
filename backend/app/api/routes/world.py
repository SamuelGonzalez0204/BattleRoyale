from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.world import WorldStateOut
from app.services.season import get_active_season, get_world_state

router = APIRouter(prefix="/api/world", tags=["world"])


@router.get("", response_model=WorldStateOut)
def read_world(db: Session = Depends(get_db)) -> WorldStateOut:
    try:
        season = get_active_season(db)
        state = get_world_state(db, season)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return WorldStateOut(
        season_number=season.number,
        season_name=season.name,
        phase=season.phase.value,
        poblacion=state.poblacion,
        comida=state.comida,
        moral=state.moral,
        defensa=state.defensa,
        oro=state.oro,
    )
