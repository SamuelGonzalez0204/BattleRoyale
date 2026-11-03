"""Patrocinio (Fase B): un miembro gasta Chispas para apoyar a otro de SU facción.

Lo patrocinado en la temporada decide el campeón de cada facción en La Última Luz.
Solo se patrocina en `convergencia` o `colapso` y antes de que arranque el evento.
Las Chispas se gastan (economy.spend_chispas): el patrocinado NO las recibe en su
saldo, para que el patrocinio no sirva para mover Chispas entre cuentas.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.faction import Faction
from app.models.season import Season, SeasonPhase
from app.models.sponsorship import Sponsorship
from app.models.user import User
from app.services.battle_royale.lifecycle import event_for_season
from app.services.economy import spend_chispas

SPONSOR_PHASES = frozenset({SeasonPhase.convergencia, SeasonPhase.colapso})
SPONSOR_REASON = "patrocinio"


class SponsorClosed(Exception):
    """Fuera de convergencia/colapso o con La Última Luz ya arrancada."""


class SponsorForbidden(Exception):
    """Sin facción o patrocinando a alguien de otra facción."""


class SponsorInvalid(Exception):
    """Patrocinarse a uno mismo."""


class RecipientNotFound(Exception):
    pass


@dataclass(frozen=True)
class SponsoredMember:
    user_id: uuid.UUID
    handle: str
    total_chispas: int
    sponsorships: int


@dataclass(frozen=True)
class FactionSponsorBoard:
    faction_slug: str
    faction_name: str
    members: list[SponsoredMember]


def sponsoring_is_open(phase: SeasonPhase, has_event: bool) -> bool:
    """Regla pura: ¿se puede patrocinar ahora?"""
    return SeasonPhase(phase) in SPONSOR_PHASES and not has_event


def _check_sponsor(db: Session, season: Season, sponsor: User, recipient_id: uuid.UUID) -> User:
    if not sponsoring_is_open(season.phase, event_for_season(db, season) is not None):
        raise SponsorClosed("Solo se patrocina en convergencia o colapso, antes de La Última Luz")
    if recipient_id == sponsor.id:
        raise SponsorInvalid("No puedes patrocinarte a ti mismo")
    if sponsor.faction_id is None:
        raise SponsorForbidden("Necesitas una facción para patrocinar")
    recipient = db.get(User, recipient_id)
    if recipient is None:
        raise RecipientNotFound("Esa cuenta no existe")
    if recipient.faction_id != sponsor.faction_id:
        raise SponsorForbidden("Solo puedes patrocinar a miembros de tu facción")
    return recipient


def sponsor_member(
    db: Session, season: Season, sponsor: User, recipient_id: uuid.UUID, chispas: int, now: datetime
) -> Sponsorship:
    """Gasta `chispas` (≥1) del patrocinador. Lanza SponsorClosed, SponsorInvalid,
    SponsorForbidden, RecipientNotFound o economy.InsufficientChispas sin cambios.
    Bloquea la temporada para no colarse a la vez que arranca el evento. Hace commit."""
    if chispas < 1:
        raise ValueError("chispas debe ser al menos 1")
    try:
        locked = db.query(Season).filter(Season.id == season.id).with_for_update().one()
        recipient = _check_sponsor(db, locked, sponsor, recipient_id)
        spend_chispas(db, sponsor, chispas, reason=SPONSOR_REASON)
    except Exception:
        db.rollback()
        raise
    sponsorship = Sponsorship(
        season_id=locked.id,
        sponsor_id=sponsor.id,
        recipient_id=recipient.id,
        faction_id=recipient.faction_id,
        chispas=chispas,
        created_at=now,
    )
    db.add(sponsorship)
    db.commit()
    return sponsorship


def _faction_board(db: Session, season: Season, faction: Faction, limit: int) -> FactionSponsorBoard:
    total = func.sum(Sponsorship.chispas)
    rows = (
        db.query(User.id, User.handle, total, func.count(Sponsorship.id))
        .join(Sponsorship, Sponsorship.recipient_id == User.id)
        .filter(Sponsorship.season_id == season.id, User.faction_id == faction.id)
        .group_by(User.id, User.handle)
        .order_by(total.desc(), func.min(Sponsorship.created_at).asc(), User.handle.asc())
        .limit(limit)
        .all()
    )
    members = [SponsoredMember(user_id, handle, int(chispas), int(count)) for user_id, handle, chispas, count in rows]
    return FactionSponsorBoard(faction_slug=faction.slug, faction_name=faction.name, members=members)


def sponsor_leaderboard(db: Session, season: Season, limit: int) -> list[FactionSponsorBoard]:
    """Por facción (orden por slug), sus miembros más patrocinados en la temporada."""
    factions = db.query(Faction).order_by(Faction.slug.asc()).all()
    return [_faction_board(db, season, faction, limit) for faction in factions]
