"""Tests HTTP de /api/decisions contra la BD de tests (override de get_db)."""

import uuid
from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.db.session import get_db
from app.main import app
from app.models.decision import Decision
from app.models.season import Season, SeasonPhase
from app.models.user import User
from app.models.world import WorldState
from app.services.daily_decision import close_decision

pytestmark = pytest.mark.integration

STATS = {"poblacion": 50, "comida": 50, "moral": 50, "defensa": 50, "oro": 50}


@pytest.fixture()
def client(db: Session) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    try:
        # Sin `with`: no arranca el lifespan, así el scheduler no toca la BD real.
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def active_season(db: Session) -> Season:
    now = datetime.now(timezone.utc)
    season = Season(
        number=901,
        name="Temporada HTTP",
        phase=SeasonPhase.construccion,
        is_active=True,
        started_at=now,
        phase_started_at=now,
    )
    db.add(season)
    db.flush()
    db.add(WorldState(season_id=season.id, **STATS))
    db.commit()
    return season


@pytest.fixture()
def auth_headers(db: Session) -> dict[str, str]:
    tag = uuid.uuid4().hex[:10]
    user = User(email=f"{tag}@test.local", handle=f"http_{tag}", hashed_password="x", chispas=10)
    db.add(user)
    db.commit()
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


def test_today_exposes_additive_phase_a_fields(client, active_season, auth_headers) -> None:
    response = client.get("/api/decisions/today", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    for legacy in ("id", "question", "option_a", "option_b", "closes_at", "votes_a", "votes_b", "my_vote"):
        assert legacy in body
    assert body["effects_a"] and body["effects_b"]
    assert body["role_affinity"] in {"mercader", "guardia", "cronista", "explorador"}
    assert body["closed"] is False
    assert body["winner"] is None


def test_vote_on_open_decision_counts_chispas_weight(client, active_season, auth_headers) -> None:
    response = client.post(
        "/api/decisions/today/vote", json={"option": "b", "chispas_to_spend": 3}, headers=auth_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["my_vote"] == "b"
    assert body["votes_b"] == 4 and body["votes_a"] == 0


def test_vote_on_closed_decision_is_rejected(client, db, active_season, auth_headers) -> None:
    decision_id = client.get("/api/decisions/today", headers=auth_headers).json()["id"]
    close_decision(db, db.get(Decision, uuid.UUID(decision_id)))

    response = client.post("/api/decisions/today/vote", json={"option": "a"}, headers=auth_headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "La decisión de hoy ya cerró"
    assert client.get("/api/decisions/today", headers=auth_headers).json()["closed"] is True


def test_anonymous_today_request_is_unauthorized_not_a_crash(client, active_season) -> None:
    response = client.get("/api/decisions/today")

    assert response.status_code == 401
