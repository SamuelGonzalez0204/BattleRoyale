"""HTTP de verificación de handle (C5), reports (C6) y Chispas sin verificar (C2)."""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.models.faction import Faction
from app.models.report import Report

pytestmark = pytest.mark.integration


# --- C5: verificación de handle ---------------------------------------------


def test_me_exposes_handle_verification_none_by_default(api, make_user) -> None:
    _, headers = make_user()

    body = api.get("/api/users/me", headers=headers).json()

    assert body["handle_verification_status"] == "none"
    assert body["handle_verification_code"] is None


def test_request_handle_verification_creates_pending_code(api, make_user) -> None:
    _, headers = make_user()

    response = api.post("/api/users/me/handle-verification", headers=headers)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["code"].startswith("CICLO-")
    me = api.get("/api/users/me", headers=headers).json()
    assert me["handle_verification_status"] == "pending"
    assert me["handle_verification_code"] == body["code"]


def test_requesting_again_rotates_the_code(api, make_user) -> None:
    _, headers = make_user()

    first = api.post("/api/users/me/handle-verification", headers=headers).json()["code"]
    second = api.post("/api/users/me/handle-verification", headers=headers).json()["code"]

    assert first != second


def test_verified_handle_cannot_request_again(api, db: Session, make_user) -> None:
    from app.models.user import HandleVerificationStatus

    user, headers = make_user()
    user.handle_verification_status = HandleVerificationStatus.verified
    db.commit()

    response = api.post("/api/users/me/handle-verification", headers=headers)

    assert response.status_code == 409


# --- C6: reports --------------------------------------------------------------


def test_report_another_user(api, db: Session, make_user) -> None:
    reporter, headers = make_user()
    target, _ = make_user()

    response = api.post(
        "/api/reports",
        json={"reported_user_id": str(target.id), "reason": "bot", "details": "Vota cada segundo"},
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "open"
    assert body["reason"] == "bot"
    report = db.get(Report, uuid.UUID(body["id"]))
    assert report.reporter_id == reporter.id and report.reported_user_id == target.id


def test_report_requires_auth(api, make_user) -> None:
    target, _ = make_user()

    response = api.post("/api/reports", json={"reported_user_id": str(target.id), "reason": "bot"})

    assert response.status_code == 401


def test_cannot_report_yourself(api, make_user) -> None:
    me, headers = make_user()

    response = api.post("/api/reports", json={"reported_user_id": str(me.id), "reason": "abuso"}, headers=headers)

    assert response.status_code == 400


def test_report_unknown_user_is_404(api, make_user) -> None:
    _, headers = make_user()

    response = api.post(
        "/api/reports", json={"reported_user_id": str(uuid.uuid4()), "reason": "otro"}, headers=headers
    )

    assert response.status_code == 404


def test_duplicate_open_report_is_409(api, make_user) -> None:
    _, headers = make_user()
    target, _ = make_user()
    payload = {"reported_user_id": str(target.id), "reason": "suplantacion"}

    first = api.post("/api/reports", json=payload, headers=headers)
    second = api.post("/api/reports", json={**payload, "reason": "abuso"}, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 409


def test_report_validates_reason_and_details_length(api, make_user) -> None:
    _, headers = make_user()
    target, _ = make_user()

    bad_reason = api.post(
        "/api/reports", json={"reported_user_id": str(target.id), "reason": "spam"}, headers=headers
    )
    long_details = api.post(
        "/api/reports",
        json={"reported_user_id": str(target.id), "reason": "otro", "details": "x" * 501},
        headers=headers,
    )

    assert bad_reason.status_code == 422
    assert long_details.status_code == 422


def test_reports_are_rate_limited_per_user(api, make_user) -> None:
    _, headers = make_user()
    targets = [make_user()[0] for _ in range(11)]

    codes = [
        api.post("/api/reports", json={"reported_user_id": str(t.id), "reason": "bot"}, headers=headers).status_code
        for t in targets
    ]

    assert codes[:10] == [201] * 10
    assert codes[10] == 429


# --- C2: el Augurio no da Chispas a cuentas sin verificar ---------------------


@pytest.fixture()
def factions(db: Session) -> None:
    # La migración 0002 ya siembra las facciones; si faltasen, el test no tendría sentido.
    assert db.query(Faction).count() > 0


def test_augurio_welcome_bonus_requires_verified_email(api, factions, make_user) -> None:
    _, unverified = make_user(is_verified=False)
    _, verified = make_user(is_verified=True)

    api.post("/api/augurio/assign", headers=unverified)
    api.post("/api/augurio/assign", headers=verified)

    assert api.get("/api/users/me", headers=unverified).json()["chispas"] == 0
    assert api.get("/api/users/me", headers=verified).json()["chispas"] == 10
