"""GET /api/factions/me/members: miembros de mi facción para la UI de patrocinio."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.models.season import SeasonPhase
from app.models.sponsorship import Sponsorship
from tests.br_support import faction, make_season, member

pytestmark = pytest.mark.integration

NOW = datetime(2026, 12, 1, 12, 0, tzinfo=timezone.utc)
URL = "/api/factions/me/members"


def _sponsor(db: Session, season, sponsor, recipient, chispas: int) -> None:
    db.add(
        Sponsorship(
            season_id=season.id,
            sponsor_id=sponsor.id,
            recipient_id=recipient.id,
            faction_id=recipient.faction_id,
            chispas=chispas,
            created_at=NOW,
        )
    )
    db.commit()


def test_requires_a_session(api) -> None:
    assert api.get(URL).status_code == 401


def test_without_faction_is_403(db: Session, api) -> None:
    _, headers = member(db, None)

    response = api.get(URL, headers=headers)

    assert response.status_code == 403
    assert "facción" in response.json()["detail"]


def test_lists_my_faction_without_me_with_this_season_sponsorship(db: Session, api) -> None:
    season = make_season(db, 970, SeasonPhase.convergencia, NOW)
    old = make_season(db, 969, SeasonPhase.colapso, NOW - timedelta(days=60))
    old.is_active = False
    db.commit()
    culto = faction(db, "culto")
    me, headers = member(db, culto, handle="mm_yo")
    star, _ = member(db, culto, handle="mm_estrella")
    quiet, _ = member(db, culto, handle="mm_calma")
    member(db, faction(db, "orden"), handle="mm_ajeno")
    _sponsor(db, season, me, star, 7)
    _sponsor(db, season, quiet, star, 3)
    _sponsor(db, old, me, quiet, 40)

    response = api.get(URL, params={"q": "mm_"}, headers=headers)

    assert response.status_code == 200
    assert response.json() == [
        {"user_id": str(star.id), "handle": "mm_estrella", "role": None, "sponsored_total": 10},
        {"user_id": str(quiet.id), "handle": "mm_calma", "role": None, "sponsored_total": 0},
    ]


def test_filters_by_case_insensitive_handle_prefix_and_limits(db: Session, api) -> None:
    gremio = faction(db, "gremio")
    _, headers = member(db, gremio, handle="pf_yo")
    for name in ("pf_Ana", "pf_anibal", "pf_bea"):
        member(db, gremio, handle=name)

    body = api.get(URL, params={"q": "PF_AN", "limit": 1}, headers=headers).json()

    assert [m["handle"] for m in body] == ["pf_Ana"]


def test_like_wildcards_in_q_are_literal(db: Session, api) -> None:
    gremio = faction(db, "gremio")
    _, headers = member(db, gremio, handle="wc_yo")
    member(db, gremio, handle="wc_otro")

    body = api.get(URL, params={"q": "%"}, headers=headers).json()

    assert body == []


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 51}, {"q": "x" * 61}])
def test_invalid_params_are_422(db: Session, api, params) -> None:
    _, headers = member(db, faction(db, "gremio"))

    assert api.get(URL, params=params, headers=headers).status_code == 422
