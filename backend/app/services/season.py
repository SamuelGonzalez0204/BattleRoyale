from sqlalchemy.orm import Session

from app.models.season import Season
from app.models.world import WorldState


def get_active_season(db: Session) -> Season:
    season = db.query(Season).filter(Season.is_active.is_(True)).order_by(Season.number.desc()).first()
    if season is None:
        raise ValueError("No hay una temporada activa configurada")
    return season


def get_world_state(db: Session, season: Season) -> WorldState:
    state = db.query(WorldState).filter(WorldState.season_id == season.id).first()
    if state is None:
        raise ValueError("La temporada activa no tiene estado de mundo todavía")
    return state
