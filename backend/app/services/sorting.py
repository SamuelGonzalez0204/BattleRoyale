"""El Augurio: asigna facción nueva balanceando la cuota entre las tres,
sin que el reparto se sienta 100% determinista para quien lo vive."""

import random

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.faction import Faction
from app.models.user import User


def faction_counts(db: Session) -> dict[str, int]:
    rows = (
        db.query(Faction.id, func.count(User.id))
        .outerjoin(User, User.faction_id == Faction.id)
        .group_by(Faction.id)
        .all()
    )
    return {str(faction_id): count for faction_id, count in rows}


def compute_weights(
    member_counts: list[int],
    target_share: float,
    base_weight: float,
) -> list[float]:
    """Peso de cada facción = cuánto le falta para su cuota objetivo + un
    peso base que garantiza que ninguna facción llegue nunca a probabilidad 0.
    Pura función, sin tocar la base de datos: fácil de testear.
    """
    total = sum(member_counts) or 1
    weights = []
    for count in member_counts:
        current_share = count / total
        deficit = max(0.0, target_share - current_share)
        weights.append(deficit + base_weight)
    return weights


def assign_faction(db: Session, rng: random.Random | None = None) -> Faction:
    """Elige una facción con un peso que favorece a la que está por debajo
    de su cuota objetivo, dejando siempre un margen de azar real.
    """
    settings = get_settings()
    rng = rng or random.Random()

    factions = db.query(Faction).order_by(Faction.slug).all()
    if not factions:
        raise ValueError("No hay facciones configuradas todavía")

    counts = faction_counts(db)
    member_counts = [counts.get(str(f.id), 0) for f in factions]
    weights = compute_weights(member_counts, settings.augurio_target_share, settings.augurio_base_weight)

    chosen = rng.choices(factions, weights=weights, k=1)[0]
    return chosen
