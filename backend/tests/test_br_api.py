"""Fase B: HTTP de /api/br/* y /api/admin/br/* contra la BD de tests."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.models.battle_royale import BattleRoyaleEvent, Champion, Duel
from app.models.season import Season, SeasonPhase
from app.models.user import User
from app.services.battle_royale.resolution import MAX_WOUNDS
from tests.br_support import faction, make_season, member

pytestmark = pytest.mark.integration

ZERO_UUID = "00000000-0000-0000-0000-000000000000"


@pytest.fixture()
def season(db: Session) -> Season:
    return make_season(db, 970, SeasonPhase.colapso, datetime.now(timezone.utc) - timedelta(days=1))


@pytest.fixture()
def admin(db: Session):
    return member(db, None, is_admin=True)


@pytest.fixture()
def players(db: Session, season: Season) -> dict:
    gremio, orden = faction(db, "gremio"), faction(db, "orden")
    return {
        "gremio": member(db, gremio, chispas=10),
        "gremio_b": member(db, gremio),
        "orden": member(db, orden, chispas=3),
        "nofaction": member(db, None, chispas=10),
    }


@pytest.fixture()
def started(api, admin, players) -> dict:
    response = api.post("/api/admin/br/start", headers=admin[1])
    assert response.status_code == 201, response.text
    return response.json()


def _champion_headers(db: Session, players: dict, slug: str) -> dict:
    event = db.query(BattleRoyaleEvent).order_by(BattleRoyaleEvent.started_at.desc()).first()
    champion = (
        db.query(Champion).filter(Champion.event_id == event.id, Champion.faction_id == faction(db, slug).id).one()
    )
    return next(headers for user, headers in players.values() if user.id == champion.user_id)


def _finish_event(api, admin, players) -> None:
    # Gremio vota (0.5) y orden no (0 < 0.85 · 0.5): orden cae en MAX_WOUNDS rondas.
    for _ in range(MAX_WOUNDS):
        duel_id = api.get("/api/br/state", headers=admin[1]).json()["current_duel"]["id"]
        api.post(f"/api/br/duels/{duel_id}/vote", json={"tactic": "ataque"}, headers=players["gremio"][1])
        assert api.post("/api/admin/br/resolve-round", headers=admin[1]).status_code == 200


# --- Acceso ------------------------------------------------------------------

USER_ENDPOINTS = [
    ("get", "/api/br/state"),
    ("post", f"/api/br/duels/{ZERO_UUID}/vote"),
    ("post", "/api/br/seal"),
]
ADMIN_ENDPOINTS = [("post", "/api/admin/br/start"), ("post", "/api/admin/br/resolve-round")]


@pytest.mark.parametrize(("method", "path"), USER_ENDPOINTS + ADMIN_ENDPOINTS)
def test_br_endpoints_require_a_session(api, method, path) -> None:
    assert getattr(api, method)(path).status_code == 401


@pytest.mark.parametrize(("method", "path"), ADMIN_ENDPOINTS)
def test_admin_br_endpoints_reject_non_admins(api, db: Session, method, path) -> None:
    _, headers = member(db, None)

    assert getattr(api, method)(path, headers=headers).status_code == 403


# --- Estado ------------------------------------------------------------------


def test_state_without_event_is_none(api, db: Session, season: Season) -> None:
    _, headers = member(db, None)

    body = api.get("/api/br/state", headers=headers).json()

    assert body["status"] == "none"
    assert body["season_number"] == 970
    assert body["total_rounds"] == 7
    assert [zone["id"] for zone in body["zones"]] == [
        "bahia", "campos", "bosque", "cementerio", "muralla", "plaza", "cumbres",
    ]
    assert body["current_duel"] is None and body["champions"] == []
    assert [option["id"] for option in body["seal"]["options"]] == ["abundancia", "muralla", "oro", "eco", "cuna"]


def test_admin_start_returns_the_active_event(started) -> None:
    assert started["status"] == "active"
    assert started["round_number"] == 1 and started["current_zone"] == "bahia"
    assert [c["faction_slug"] for c in started["champions"]] == ["gremio", "orden"]
    assert all(c["alive"] and c["wounds"] == 0 and c["max_wounds"] == 3 for c in started["champions"])


def test_admin_start_twice_is_a_conflict(api, admin, started) -> None:
    assert api.post("/api/admin/br/start", headers=admin[1]).status_code == 409


def test_admin_start_needs_two_factions_with_members(api, admin, season: Season, db: Session) -> None:
    member(db, faction(db, "gremio"))

    response = api.post("/api/admin/br/start", headers=admin[1])

    assert response.status_code == 409
    assert "al menos 2" in response.json()["detail"]


def test_daily_decision_is_409_during_the_event(api, players, started) -> None:
    response = api.get("/api/decisions/today", headers=players["gremio"][1])

    assert response.status_code == 409
    assert "Última Luz" in response.json()["detail"]


def test_state_only_shows_my_faction_totals(api, players, started) -> None:
    duel_id = started["current_duel"]["id"]
    api.post(f"/api/br/duels/{duel_id}/vote", json={"tactic": "astucia", "chispas_to_spend": 2},
             headers=players["orden"][1])

    gremio_view = api.get("/api/br/state", headers=players["gremio"][1]).json()["current_duel"]
    orden_view = api.get("/api/br/state", headers=players["orden"][1]).json()["current_duel"]

    assert gremio_view["my_faction_totals"] == {"ataque": 0, "defensa": 0, "astucia": 0}
    assert gremio_view["has_voted"] is False and gremio_view["can_vote"] is True
    assert orden_view["my_faction_totals"] == {"ataque": 0, "defensa": 0, "astucia": 3}
    assert orden_view["has_voted"] is True and orden_view["my_tactic"] == "astucia"
    assert orden_view["can_vote"] is False


# --- Votos de táctica --------------------------------------------------------


def test_vote_spends_chispas_and_returns_my_faction_totals(api, db: Session, players, started) -> None:
    duel_id = started["current_duel"]["id"]

    response = api.post(f"/api/br/duels/{duel_id}/vote", json={"tactic": "ataque", "chispas_to_spend": 4},
                        headers=players["gremio"][1])

    assert response.status_code == 201
    body = response.json()
    assert body["weight"] == 5 and body["chispas_spent"] == 4 and body["my_chispas"] == 6
    assert body["my_faction_totals"]["ataque"] == 5 and body["my_faction_voters"] == 1


def test_second_vote_in_the_same_duel_is_a_conflict(api, players, started) -> None:
    url = f"/api/br/duels/{started['current_duel']['id']}/vote"
    api.post(url, json={"tactic": "ataque"}, headers=players["gremio"][1])

    assert api.post(url, json={"tactic": "defensa"}, headers=players["gremio"][1]).status_code == 409


def test_vote_without_faction_is_forbidden(api, players, started) -> None:
    url = f"/api/br/duels/{started['current_duel']['id']}/vote"

    assert api.post(url, json={"tactic": "ataque"}, headers=players["nofaction"][1]).status_code == 403


def test_vote_with_insufficient_chispas_is_400_and_spends_nothing(api, db: Session, players, started) -> None:
    url = f"/api/br/duels/{started['current_duel']['id']}/vote"

    response = api.post(url, json={"tactic": "ataque", "chispas_to_spend": 4}, headers=players["orden"][1])

    assert response.status_code == 400
    db.expire_all()
    assert db.get(User, players["orden"][0].id).chispas == 3
    assert api.post(url, json={"tactic": "ataque"}, headers=players["orden"][1]).status_code == 201


def test_vote_on_unknown_duel_is_404(api, players, started) -> None:
    response = api.post(f"/api/br/duels/{ZERO_UUID}/vote", json={"tactic": "ataque"}, headers=players["gremio"][1])

    assert response.status_code == 404


@pytest.mark.parametrize("payload", [{"tactic": "magia"}, {"tactic": "ataque", "chispas_to_spend": -1}, {}])
def test_vote_validation_errors_are_422(api, players, started, payload) -> None:
    url = f"/api/br/duels/{started['current_duel']['id']}/vote"

    assert api.post(url, json=payload, headers=players["gremio"][1]).status_code == 422


def test_vote_on_a_resolved_duel_is_a_conflict(api, admin, players, started) -> None:
    url = f"/api/br/duels/{started['current_duel']['id']}/vote"
    api.post("/api/admin/br/resolve-round", headers=admin[1])

    assert api.post(url, json={"tactic": "ataque"}, headers=players["gremio"][1]).status_code == 409


def test_eliminated_faction_cannot_vote(api, admin, players, started) -> None:
    _finish_event(api, admin, players)
    duel_id = started["current_duel"]["id"]

    response = api.post(f"/api/br/duels/{duel_id}/vote", json={"tactic": "ataque"}, headers=players["orden"][1])

    assert response.status_code == 409  # el evento terminó: ningún duelo abierto


# --- Resolver ronda (admin) --------------------------------------------------


def test_resolve_round_reveals_tactics_and_opens_the_next_zone(api, admin, players, started) -> None:
    url = f"/api/br/duels/{started['current_duel']['id']}/vote"
    api.post(url, json={"tactic": "ataque"}, headers=players["gremio"][1])
    api.post(url, json={"tactic": "defensa"}, headers=players["orden"][1])

    body = api.post("/api/admin/br/resolve-round", headers=admin[1]).json()

    # Gremio 1/2 = 0.5 · Orden 1/1 = 1.0 y defensa vence a ataque → 1.15
    last = body["last_round"]
    assert last["round_number"] == 1 and last["zone"] == "bahia"
    assert last["wounded_faction_slug"] == "gremio" and last["eliminated_faction_slug"] is None
    assert last["reason"] == "below_gap"
    assert {f["faction_slug"]: f["tactic"] for f in last["factions"]} == {"gremio": "ataque", "orden": "defensa"}
    assert {f["faction_slug"]: f["score"] for f in last["factions"]} == {"gremio": 0.5, "orden": 1.15}
    assert body["fallen_zones"] == ["bahia"]
    assert body["round_number"] == 2 and body["current_zone"] == "campos"
    assert body["zones"][0] == {"id": "bahia", "name": "Bahía del Gremio", "fallen": True, "fall_order": 1,
                                "is_arena": False}


def test_resolve_round_without_event_is_a_conflict(api, admin, season: Season) -> None:
    assert api.post("/api/admin/br/resolve-round", headers=admin[1]).status_code == 409


# --- Sello -------------------------------------------------------------------


def test_seal_while_the_event_runs_is_a_conflict(api, players, started) -> None:
    response = api.post("/api/br/seal", json={"seal": "oro"}, headers=players["gremio"][1])

    assert response.status_code == 409


def test_seal_without_any_event_is_404(api, players) -> None:
    assert api.post("/api/br/seal", json={"seal": "oro"}, headers=players["gremio"][1]).status_code == 404


def test_only_the_winning_champion_can_seal(api, db: Session, admin, players, started) -> None:
    _finish_event(api, admin, players)
    winner_headers = _champion_headers(db, players, "gremio")
    other = next(h for (u, h) in (players["gremio"], players["gremio_b"]) if h != winner_headers)

    state = api.get("/api/br/state", headers=winner_headers).json()
    forbidden = api.post("/api/br/seal", json={"seal": "oro"}, headers=other)

    assert state["status"] == "finished" and state["winner"]["faction_slug"] == "gremio"
    assert state["seal"]["can_choose"] is True and state["seal"]["deadline"] is not None
    assert forbidden.status_code == 403


def test_champion_seal_opens_the_next_season(api, db: Session, admin, players, started) -> None:
    _finish_event(api, admin, players)

    response = api.post("/api/br/seal", json={"seal": "muralla"}, headers=_champion_headers(db, players, "gremio"))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["seal"] == "muralla" and body["previous_season_number"] == 970
    assert body["new_season"]["number"] == 971 and body["new_season"]["phase"] == "construccion"
    assert body["world"] == {"poblacion": 68, "comida": 41, "moral": 55, "defensa": 87, "oro": 36}

    state = api.get("/api/br/state", headers=admin[1]).json()
    assert state["status"] == "sealed" and state["seal"]["selected"] == "muralla"
    assert state["season_number"] == 970 and state["next_season_number"] == 971
    assert api.post("/api/br/seal", json={"seal": "oro"}, headers=admin[1]).status_code == 409


def test_admin_can_seal(api, admin, players, started) -> None:
    _finish_event(api, admin, players)

    assert api.post("/api/br/seal", json={"seal": "cuna"}, headers=admin[1]).status_code == 200


def test_invalid_seal_is_422(api, players) -> None:
    assert api.post("/api/br/seal", json={"seal": "dragon"}, headers=players["gremio"][1]).status_code == 422


def test_duels_are_persisted_per_round(db: Session, api, admin, players, started) -> None:
    _finish_event(api, admin, players)

    event = db.query(BattleRoyaleEvent).filter(BattleRoyaleEvent.id == started["event_id"]).one()
    duels = db.query(Duel).filter(Duel.event_id == event.id).order_by(Duel.round_number).all()
    assert [duel.zone for duel in duels] == ["bahia", "campos", "bosque"]
    assert all(duel.is_resolved for duel in duels)
