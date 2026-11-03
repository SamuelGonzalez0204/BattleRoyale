"""D4: panel de admin (/api/admin/*). Integración contra la BD de tests."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.models.decision import Decision, Vote
from app.models.report import Report, ReportReason, ReportStatus
from app.models.season import Season, SeasonPhase
from app.models.user import HandleVerificationStatus
from app.models.world import WorldState

pytestmark = pytest.mark.integration

STATS = {"poblacion": 50, "comida": 50, "moral": 50, "defensa": 50, "oro": 50}
EMERGENCY = {
    "question": "Una riada amenaza el molino. ¿Qué hacemos?",
    "option_a": "Reforzar el dique",
    "option_b": "Evacuar el valle",
    "effects_a": {"defensa": 5, "oro": -5},
    "effects_b": {"poblacion": -3, "moral": 4},
    "role_affinity": "guardia",
}


@pytest.fixture()
def admin(db: Session, make_user):
    user, headers = make_user()
    user.is_admin = True
    db.commit()
    return user, headers


@pytest.fixture()
def season(db: Session) -> Season:
    now = datetime.now(timezone.utc)
    season = Season(
        number=950,
        name="Temporada Admin",
        phase=SeasonPhase.construccion,
        is_active=True,
        started_at=now,
        phase_started_at=now - timedelta(days=1),
    )
    db.add(season)
    db.flush()
    db.add(WorldState(season_id=season.id, **STATS))
    db.commit()
    return season


ADMIN_ENDPOINTS = [
    ("get", "/api/admin/seasons"),
    ("post", "/api/admin/seasons/00000000-0000-0000-0000-000000000000/advance-phase"),
    ("post", "/api/admin/decisions/emergency"),
    ("get", "/api/admin/reports"),
    ("post", "/api/admin/reports/00000000-0000-0000-0000-000000000000"),
    ("get", "/api/admin/handles"),
    ("post", "/api/admin/handles/00000000-0000-0000-0000-000000000000"),
]


# --- Acceso ------------------------------------------------------------------


@pytest.mark.parametrize(("method", "path"), ADMIN_ENDPOINTS)
def test_admin_endpoints_reject_non_admins_with_403(api, make_user, method, path) -> None:
    _, headers = make_user()

    response = getattr(api, method)(path, headers=headers, **({"json": {}} if method == "post" else {}))

    assert response.status_code == 403


@pytest.mark.parametrize(("method", "path"), ADMIN_ENDPOINTS)
def test_admin_endpoints_require_a_session(api, method, path) -> None:
    response = getattr(api, method)(path)

    assert response.status_code == 401


def test_me_exposes_is_admin(api, admin, make_user) -> None:
    _, plain_headers = make_user()

    assert api.get("/api/users/me", headers=admin[1]).json()["is_admin"] is True
    assert api.get("/api/users/me", headers=plain_headers).json()["is_admin"] is False


# --- Temporadas ----------------------------------------------------------------


def test_list_seasons_includes_phase_and_next_phase(api, admin, season) -> None:
    response = api.get("/api/admin/seasons", headers=admin[1])

    assert response.status_code == 200
    item = next(s for s in response.json() if s["id"] == str(season.id))
    assert item["phase"] == "construccion"
    assert item["next_phase"] == "conflicto"
    assert item["is_active"] is True


def test_advance_phase_moves_one_phase_and_resets_phase_clock(api, admin, season, db: Session) -> None:
    before = season.phase_started_at

    response = api.post(f"/api/admin/seasons/{season.id}/advance-phase", headers=admin[1])

    assert response.status_code == 200
    assert response.json()["phase"] == "conflicto"
    db.refresh(season)
    assert season.phase == SeasonPhase.conflicto
    assert season.phase_started_at > before


def test_advance_phase_never_goes_past_colapso(api, admin, season, db: Session) -> None:
    season.phase = SeasonPhase.colapso
    db.commit()

    response = api.post(f"/api/admin/seasons/{season.id}/advance-phase", headers=admin[1])

    assert response.status_code == 409
    db.refresh(season)
    assert season.phase == SeasonPhase.colapso


def test_advance_phase_of_unknown_season_is_404(api, admin) -> None:
    response = api.post(
        "/api/admin/seasons/00000000-0000-0000-0000-000000000000/advance-phase", headers=admin[1]
    )

    assert response.status_code == 404


# --- Decisión de emergencia ------------------------------------------------------


def _today_decision(db: Session, season: Season) -> Decision | None:
    today = datetime.now(timezone.utc).date()
    return db.query(Decision).filter(Decision.season_id == season.id, Decision.day == today).first()


def test_emergency_decision_is_created_when_today_has_none(api, admin, season, db: Session) -> None:
    response = api.post("/api/admin/decisions/emergency", headers=admin[1], json=EMERGENCY)

    assert response.status_code == 201
    body = response.json()
    assert body["question"] == EMERGENCY["question"]
    assert body["effects_a"] == EMERGENCY["effects_a"]
    assert body["role_affinity"] == "guardia"
    decision = _today_decision(db, season)
    assert decision is not None and str(decision.id) == body["id"]


def test_emergency_decision_replaces_today_without_votes(api, admin, season, db: Session) -> None:
    first = api.post("/api/admin/decisions/emergency", headers=admin[1], json=EMERGENCY).json()

    second = api.post(
        "/api/admin/decisions/emergency",
        headers=admin[1],
        json={**EMERGENCY, "question": "Otra pregunta", "role_affinity": None},
    )

    assert second.status_code == 201
    assert second.json()["id"] == first["id"]
    decision = _today_decision(db, season)
    db.refresh(decision)
    assert decision.question == "Otra pregunta"
    assert decision.role_affinity is None


def test_emergency_decision_conflicts_when_today_has_votes(api, admin, season, db: Session, make_user) -> None:
    created = api.post("/api/admin/decisions/emergency", headers=admin[1], json=EMERGENCY).json()
    voter, _ = make_user()
    db.add(Vote(decision_id=created["id"], user_id=voter.id, option="a", weight=1))
    db.commit()

    response = api.post("/api/admin/decisions/emergency", headers=admin[1], json=EMERGENCY)

    assert response.status_code == 409


def test_emergency_decision_rejects_unknown_stats(api, admin, season) -> None:
    payload = {**EMERGENCY, "effects_a": {"magia": 3}}

    response = api.post("/api/admin/decisions/emergency", headers=admin[1], json=payload)

    assert response.status_code == 422


# --- Reports ---------------------------------------------------------------------


@pytest.fixture()
def open_report(db: Session, make_user) -> Report:
    reporter, _ = make_user()
    reported, _ = make_user()
    report = Report(reporter_id=reporter.id, reported_user_id=reported.id, reason=ReportReason.bot)
    db.add(report)
    db.commit()
    return report


def test_list_reports_filters_by_status_open_by_default(api, admin, open_report) -> None:
    response = api.get("/api/admin/reports", headers=admin[1])

    assert response.status_code == 200
    item = next(r for r in response.json() if r["id"] == str(open_report.id))
    assert item["status"] == "open"
    assert item["reporter_handle"].startswith("u_")
    assert item["reported_handle"].startswith("u_")


def test_moderate_report_sets_status(api, admin, open_report, db: Session) -> None:
    response = api.post(f"/api/admin/reports/{open_report.id}", headers=admin[1], json={"status": "dismissed"})

    assert response.status_code == 200
    assert response.json()["status"] == "dismissed"
    db.refresh(open_report)
    assert open_report.status == ReportStatus.dismissed
    listed = api.get("/api/admin/reports?status=open", headers=admin[1]).json()
    assert all(r["id"] != str(open_report.id) for r in listed)


def test_moderate_report_rejects_reopening(api, admin, open_report) -> None:
    response = api.post(f"/api/admin/reports/{open_report.id}", headers=admin[1], json={"status": "open"})

    assert response.status_code == 422


def test_moderate_report_twice_conflicts(api, admin, open_report) -> None:
    api.post(f"/api/admin/reports/{open_report.id}", headers=admin[1], json={"status": "reviewed"})

    response = api.post(f"/api/admin/reports/{open_report.id}", headers=admin[1], json={"status": "dismissed"})

    assert response.status_code == 409


def test_moderate_unknown_report_is_404(api, admin) -> None:
    response = api.post(
        "/api/admin/reports/00000000-0000-0000-0000-000000000000", headers=admin[1], json={"status": "reviewed"}
    )

    assert response.status_code == 404


# --- Handles ---------------------------------------------------------------------


@pytest.fixture()
def pending_user(db: Session, make_user):
    user, headers = make_user()
    user.handle_verification_status = HandleVerificationStatus.pending
    user.handle_verification_code = "CICLO-ABC234"
    user.handle_verification_requested_at = datetime.now(timezone.utc)
    db.commit()
    return user


def test_list_pending_handles(api, admin, pending_user) -> None:
    response = api.get("/api/admin/handles?status=pending", headers=admin[1])

    assert response.status_code == 200
    item = next(h for h in response.json() if h["user_id"] == str(pending_user.id))
    assert item["handle"] == pending_user.handle
    assert item["code"] == "CICLO-ABC234"


@pytest.mark.parametrize("decision", ["verified", "rejected"])
def test_review_handle_sets_status_and_reviewed_at(api, admin, pending_user, db: Session, decision) -> None:
    response = api.post(f"/api/admin/handles/{pending_user.id}", headers=admin[1], json={"decision": decision})

    assert response.status_code == 200
    assert response.json()["status"] == decision
    db.refresh(pending_user)
    assert pending_user.handle_verification_status == HandleVerificationStatus(decision)
    assert pending_user.handle_verification_reviewed_at is not None


def test_review_handle_that_is_not_pending_conflicts(api, admin, make_user) -> None:
    user, _ = make_user()

    response = api.post(f"/api/admin/handles/{user.id}", headers=admin[1], json={"decision": "verified"})

    assert response.status_code == 409


def test_review_handle_rejects_unknown_decision(api, admin, pending_user) -> None:
    response = api.post(f"/api/admin/handles/{pending_user.id}", headers=admin[1], json={"decision": "pending"})

    assert response.status_code == 422
