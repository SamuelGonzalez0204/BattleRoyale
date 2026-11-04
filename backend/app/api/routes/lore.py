"""Lore (Fase E3): pública, sin sesión, con rate limit por IP."""

from dataclasses import asdict

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.schemas.lore import LoreOut
from app.services.lore import build_lore

router = APIRouter(prefix="/api/lore", tags=["lore"])


@router.get("", response_model=LoreOut)
@limiter.limit(get_settings().rate_limit_public_read)
def read_lore(request: Request, db: Session = Depends(get_db)) -> LoreOut:
    return LoreOut.model_validate(asdict(build_lore(db)))
