"""Fase B: los endpoints de escritura de La Última Luz tienen rate limit por usuario."""

import pytest
from sqlalchemy.orm import Session

from app.core.config import get_settings
from tests.br_support import member

pytestmark = pytest.mark.integration


def test_battle_royale_writes_are_rate_limited(api, db: Session) -> None:
    assert get_settings().rate_limit_battle_royale == "30/minute"
    _, headers = member(db, None)

    codes = [api.post("/api/br/seal", json={"seal": "eco"}, headers=headers).status_code for _ in range(31)]

    assert 429 not in codes[:30]
    assert codes[30] == 429
