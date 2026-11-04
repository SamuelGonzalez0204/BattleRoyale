"""Ayudas compartidas por los tests de La Última Luz y del patrocinio (Fase B)."""

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.faction import Faction
from app.models.season import Season, SeasonPhase
from app.models.user import User
from app.models.world import WorldState

STATS = {"poblacion": 50, "comida": 50, "moral": 50, "defensa": 50, "oro": 50}


def faction(db: Session, slug: str) -> Faction:
    """Facción sembrada (gremio/orden/culto) o, si no existe, una creada para el test."""
    found = db.query(Faction).filter(Faction.slug == slug).first()
    if found is not None:
        return found
    created = Faction(slug=slug, name=f"Facción {slug}", color="#123456")
    db.add(created)
    db.commit()
    return created


def member(
    db: Session,
    of: Faction | None,
    *,
    chispas: int = 0,
    is_admin: bool = False,
    handle: str | None = None,
) -> tuple[User, dict[str, str]]:
    tag = uuid.uuid4().hex[:10]
    user = User(
        email=f"{tag}@br.test",
        handle=handle or f"br_{tag}",
        hashed_password="x",
        is_verified=True,
        chispas=chispas,
        is_admin=is_admin,
        faction_id=of.id if of else None,
    )
    db.add(user)
    db.commit()
    return user, {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


def make_season(db: Session, number: int, phase: SeasonPhase, phase_started_at: datetime) -> Season:
    season = Season(
        number=number,
        name=f"Temporada de pruebas {number}",
        phase=phase,
        is_active=True,
        started_at=phase_started_at,
        phase_started_at=phase_started_at,
    )
    db.add(season)
    db.flush()
    db.add(WorldState(season_id=season.id, **STATS))
    db.commit()
    return season
