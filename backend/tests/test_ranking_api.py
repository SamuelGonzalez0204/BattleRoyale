"""GET /api/ranking (Fase E2): Chispas actuales y votos de la temporada activa."""

from datetime import date, datetime, time, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.models.decision import Decision, Vote
from app.models.season import Season, SeasonPhase
from tests.br_support import faction, make_season, member

pytestmark = pytest.mark.integration

NOW = datetime(2026, 12, 1, 12, 0, tzinfo=timezone.utc)
URL = "/api/ranking"


@pytest.fixture()
def season(db: Session) -> Season:
    return make_season(db, 960, SeasonPhase.conflicto, NOW)


def _decisions(db: Session, season: Season, count: int) -> list[Decision]:
    rows = []
    for offset in range(count):
        day = date(2026, 12, 1) + timedelta(days=offset)
        decision = Decision(
            season_id=season.id,
            day=day,
            question=f"¿Pregunta {offset}?",
            option_a="A",
            option_b="B",
            closes_at=datetime.combine(day, time(23, 59), tzinfo=timezone.utc),
        )
        db.add(decision)
        rows.append(decision)
    db.commit()
    return rows


def _vote(db: Session, user, decisions: list[Decision]) -> None:
    for decision in decisions:
        db.add(Vote(decision_id=decision.id, user_id=user.id, option="a", weight=1))
    db.commit()


def test_requires_a_session(api) -> None:
    assert api.get(URL).status_code == 401


def test_chispas_ranking_orders_by_value_then_handle(db: Session, api, season) -> None:
    culto = faction(db, "culto")
    member(db, culto, chispas=50, handle="zeta")
    member(db, culto, chispas=50, handle="alfa")
    me, headers = member(db, culto, chispas=10, handle="medio")

    response = api.get(URL, params={"scope": "chispas", "faction": "culto"}, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert [(i["rank"], i["handle"], i["value"]) for i in body["items"]] == [
        (1, "alfa", 50),
        (1, "zeta", 50),
        (3, "medio", 10),
    ]
    assert body["total"] == 3
    assert body["items"][2] == {
        "rank": 3,
        "user_id": str(me.id),
        "handle": "medio",
        "faction_slug": "culto",
        "role": None,
        "value": 10,
    }
    assert body["me"] == {"rank": 3, "value": 10}
    assert (body["limit"], body["offset"]) == (20, 0)


def test_votes_ranking_counts_only_votes_of_the_active_season(db: Session, api, season) -> None:
    orden = faction(db, "orden")
    old = make_season(db, 959, SeasonPhase.colapso, NOW - timedelta(days=60))
    old.is_active = False
    db.commit()
    voter, headers = member(db, orden, handle="votante")
    lazy, _ = member(db, orden, handle="perezoso")
    _vote(db, voter, _decisions(db, season, 3))
    _vote(db, lazy, _decisions(db, old, 5))

    body = api.get(URL, params={"scope": "votos", "faction": "orden"}, headers=headers).json()

    values = {item["handle"]: item["value"] for item in body["items"]}
    assert values == {"votante": 3, "perezoso": 0}
    assert body["items"][0]["handle"] == "votante"
    assert body["me"] == {"rank": 1, "value": 3}


def test_pagination_keeps_global_ranks(db: Session, api, season) -> None:
    gremio = faction(db, "gremio")
    for value in range(5):
        member(db, gremio, chispas=100 + value, handle=f"pag_{value}")
    _, headers = member(db, gremio, chispas=1, handle="pag_yo")

    body = api.get(
        URL, params={"scope": "chispas", "faction": "gremio", "limit": 2, "offset": 2}, headers=headers
    ).json()

    assert [(i["rank"], i["handle"]) for i in body["items"]] == [(3, "pag_2"), (4, "pag_1")]
    assert body["total"] == 6
    assert (body["limit"], body["offset"]) == (2, 2)
    assert body["me"] == {"rank": 6, "value": 1}


def test_users_without_faction_appear_in_the_global_ranking(db: Session, api, season) -> None:
    loner, headers = member(db, None, chispas=999_999, handle="sin_bando")

    body = api.get(URL, params={"scope": "chispas", "limit": 1}, headers=headers).json()

    assert body["items"][0]["user_id"] == str(loner.id)
    assert body["items"][0]["faction_slug"] is None
    assert body["me"] == {"rank": 1, "value": 999_999}


def test_me_is_null_when_filtering_by_another_faction(db: Session, api, season) -> None:
    _, headers = member(db, faction(db, "gremio"), chispas=5)

    body = api.get(URL, params={"faction": "culto"}, headers=headers).json()

    assert body["me"] is None


def test_unknown_faction_is_404(db: Session, api, season) -> None:
    _, headers = member(db, None)

    response = api.get(URL, params={"faction": "piratas"}, headers=headers)

    assert response.status_code == 404


@pytest.mark.parametrize(
    "params",
    [{"scope": "oro"}, {"limit": 0}, {"limit": 51}, {"offset": -1}],
)
def test_invalid_params_are_422(db: Session, api, season, params) -> None:
    _, headers = member(db, None)

    assert api.get(URL, params=params, headers=headers).status_code == 422
