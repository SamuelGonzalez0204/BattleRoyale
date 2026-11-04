"""Fase B: HTTP de /api/sponsor contra la BD de tests."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.models.chispa import ChispaTransaction
from app.models.season import Season, SeasonPhase
from app.models.user import User
from app.services.sponsorship import sponsoring_is_open
from tests.br_support import faction, make_season, member

pytestmark = pytest.mark.integration

ZERO_UUID = "00000000-0000-0000-0000-000000000000"


@pytest.fixture()
def season(db: Session) -> Season:
    return make_season(db, 980, SeasonPhase.convergencia, datetime.now(timezone.utc) - timedelta(days=1))


@pytest.fixture()
def gremio_pair(db: Session, season: Season):
    gremio = faction(db, "gremio")
    return member(db, gremio, chispas=10, handle="sponsor_g1"), member(db, gremio, handle="sponsor_g2")


def _sponsor(api, headers: dict, user_id, chispas: int = 3):
    return api.post("/api/sponsor", json={"user_id": str(user_id), "chispas": chispas}, headers=headers)


@pytest.mark.parametrize(
    ("phase", "has_event", "expected"),
    [
        (SeasonPhase.construccion, False, False),
        (SeasonPhase.conflicto, False, False),
        (SeasonPhase.convergencia, False, True),
        (SeasonPhase.colapso, False, True),
        (SeasonPhase.colapso, True, False),
    ],
)
def test_sponsoring_window(phase: SeasonPhase, has_event: bool, expected: bool) -> None:
    assert sponsoring_is_open(phase, has_event) is expected


def test_sponsor_requires_a_session(api) -> None:
    assert api.post("/api/sponsor", json={"user_id": ZERO_UUID, "chispas": 1}).status_code == 401
    assert api.get("/api/sponsor/leaderboard").status_code == 401


def test_sponsor_spends_chispas_and_records_the_sponsorship(api, db: Session, gremio_pair) -> None:
    (sponsor, headers), (recipient, _) = gremio_pair

    response = _sponsor(api, headers, recipient.id, chispas=4)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["recipient_handle"] == "sponsor_g2"
    assert body["chispas"] == 4 and body["my_chispas"] == 6 and body["recipient_total"] == 4
    db.expire_all()
    assert db.get(User, recipient.id).chispas == 0  # el patrocinado no recibe saldo
    spent = db.query(ChispaTransaction).filter(ChispaTransaction.user_id == sponsor.id).one()
    assert spent.amount == -4 and spent.reason == "patrocinio"


def test_cannot_sponsor_yourself(api, gremio_pair) -> None:
    (sponsor, headers), _ = gremio_pair

    assert _sponsor(api, headers, sponsor.id).status_code == 400


def test_cannot_sponsor_another_faction(api, db: Session, gremio_pair) -> None:
    (_, headers), _ = gremio_pair
    rival, _ = member(db, faction(db, "orden"))

    assert _sponsor(api, headers, rival.id).status_code == 403


def test_cannot_sponsor_without_a_faction(api, db: Session, gremio_pair) -> None:
    _, (recipient, _) = gremio_pair
    _, headers = member(db, None, chispas=10)

    assert _sponsor(api, headers, recipient.id).status_code == 403


def test_unknown_recipient_is_404(api, gremio_pair) -> None:
    (_, headers), _ = gremio_pair

    assert _sponsor(api, headers, ZERO_UUID).status_code == 404


def test_insufficient_chispas_is_400_and_spends_nothing(api, db: Session, gremio_pair) -> None:
    (sponsor, headers), (recipient, _) = gremio_pair

    assert _sponsor(api, headers, recipient.id, chispas=11).status_code == 400
    db.expire_all()
    assert db.get(User, sponsor.id).chispas == 10


@pytest.mark.parametrize("chispas", [0, -3])
def test_sponsor_needs_at_least_one_chispa(api, gremio_pair, chispas: int) -> None:
    (_, headers), (recipient, _) = gremio_pair

    assert _sponsor(api, headers, recipient.id, chispas=chispas).status_code == 422


def test_sponsor_is_closed_before_convergencia(api, db: Session, season: Season, gremio_pair) -> None:
    (_, headers), (recipient, _) = gremio_pair
    season.phase = SeasonPhase.conflicto
    db.commit()

    response = _sponsor(api, headers, recipient.id)

    assert response.status_code == 409
    assert "convergencia" in response.json()["detail"]


def test_sponsor_is_closed_once_the_event_starts(api, db: Session, gremio_pair) -> None:
    (_, headers), (recipient, _) = gremio_pair
    member(db, faction(db, "orden"))
    admin, admin_headers = member(db, None, is_admin=True)
    assert api.post("/api/admin/br/start", headers=admin_headers).status_code == 201

    assert _sponsor(api, headers, recipient.id).status_code == 409


def test_leaderboard_ranks_members_per_faction(api, db: Session, gremio_pair) -> None:
    (g1, g1_headers), (g2, g2_headers) = gremio_pair
    g3, _ = member(db, faction(db, "gremio"), handle="sponsor_g3")
    g2.chispas = 10
    db.commit()
    _sponsor(api, g1_headers, g2.id, chispas=2)
    _sponsor(api, g1_headers, g2.id, chispas=1)
    _sponsor(api, g2_headers, g3.id, chispas=5)

    response = api.get("/api/sponsor/leaderboard?limit=5", headers=g1_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["season_number"] == 980 and body["open"] is True
    boards = {board["faction_slug"]: board for board in body["factions"]}
    assert set(boards) >= {"gremio", "orden", "culto"}
    assert [(m["handle"], m["total_chispas"], m["sponsorships"]) for m in boards["gremio"]["members"]] == [
        ("sponsor_g3", 5, 1),
        ("sponsor_g2", 3, 2),
    ]
    assert boards["orden"]["members"] == []


def test_leaderboard_limit_is_validated(api, gremio_pair) -> None:
    (_, headers), _ = gremio_pair

    assert api.get("/api/sponsor/leaderboard?limit=0", headers=headers).status_code == 422
