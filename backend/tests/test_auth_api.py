"""HTTP de /api/auth: rate limiting, verificación de email y reset de contraseña."""

import re
import uuid
from datetime import timedelta

import pytest
from sqlalchemy.orm import Session

from app.core.security import EMAIL_VERIFICATION, create_purpose_token, verify_password
from app.models.user import User

pytestmark = pytest.mark.integration

TOKEN_IN_LINK = re.compile(r"token=([A-Za-z0-9_\-\.]+)")


def _token_from(outbox) -> str:
    assert outbox.sent, "no se envió ningún correo"
    match = TOKEN_IN_LINK.search(outbox.sent[-1].body)
    assert match
    return match.group(1)


def _register_payload() -> dict[str, str]:
    tag = uuid.uuid4().hex[:10]
    return {"email": f"{tag}@example.com", "handle": f"r_{tag}", "password": "contraseña-segura"}


# --- C1: rate limiting ------------------------------------------------------


def test_twenty_registrations_from_same_ip_hit_429(api) -> None:
    codes = [api.post("/api/auth/register", json=_register_payload()).status_code for _ in range(20)]

    assert codes[:5] == [201] * 5
    assert set(codes[5:]) == {429}


def test_rate_limited_response_has_spanish_detail(api) -> None:
    payload = {"email": "nadie@example.com", "password": "loquesea123"}
    for _ in range(5):
        api.post("/api/auth/login", json=payload)

    response = api.post("/api/auth/login", json=payload)

    assert response.status_code == 429
    assert "Demasiados intentos" in response.json()["detail"]


# --- C2: verificación de email ----------------------------------------------


def test_register_sends_verification_email_and_user_starts_unverified(api, outbox) -> None:
    payload = _register_payload()

    response = api.post("/api/auth/register", json=payload)

    assert response.status_code == 201
    assert len(outbox.sent) == 1
    assert outbox.sent[0].to == payload["email"]
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    assert api.get("/api/users/me", headers=headers).json()["is_verified"] is False


def test_verify_link_marks_user_verified(api, outbox) -> None:
    response = api.post("/api/auth/register", json=_register_payload())
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    verified = api.get("/api/auth/verify", params={"token": _token_from(outbox)})

    assert verified.status_code == 200
    assert api.get("/api/users/me", headers=headers).json()["is_verified"] is True


def test_verify_rejects_invalid_token(api) -> None:
    response = api.get("/api/auth/verify", params={"token": "basura"})

    assert response.status_code == 400
    assert "no es válido" in response.json()["detail"]


def test_verify_rejects_token_issued_for_old_email(api, db: Session, make_user) -> None:
    user, _ = make_user()
    token = create_purpose_token(
        str(user.id), EMAIL_VERIFICATION, timedelta(hours=1), {"email": "otro@example.com"}
    )

    response = api.get("/api/auth/verify", params={"token": token})

    assert response.status_code == 400


def test_resend_verification_sends_new_email(api, outbox, make_user) -> None:
    _, headers = make_user(is_verified=False)

    response = api.post("/api/auth/verify/resend", headers=headers)

    assert response.status_code == 202
    assert len(outbox.sent) == 1


def test_resend_verification_for_verified_user_is_rejected(api, outbox, make_user) -> None:
    _, headers = make_user(is_verified=True)

    response = api.post("/api/auth/verify/resend", headers=headers)

    assert response.status_code == 400
    assert outbox.sent == []


def test_resend_verification_is_rate_limited(api, make_user) -> None:
    _, headers = make_user(is_verified=False)

    codes = [api.post("/api/auth/verify/resend", headers=headers).status_code for _ in range(4)]

    assert codes == [202, 202, 202, 429]


# --- C3: reset de contraseña ------------------------------------------------


def test_reset_request_for_unknown_email_returns_202_without_sending(api, outbox) -> None:
    response = api.post("/api/auth/password-reset/request", json={"email": "no-existe@example.com"})

    assert response.status_code == 202
    assert outbox.sent == []


def test_reset_request_answers_the_same_for_known_and_unknown_email(api, make_user) -> None:
    user, _ = make_user()

    known = api.post("/api/auth/password-reset/request", json={"email": user.email})
    unknown = api.post("/api/auth/password-reset/request", json={"email": "no-existe@example.com"})

    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()


def test_reset_confirm_changes_password_and_token_is_single_use(api, outbox, db: Session, make_user) -> None:
    user, _ = make_user(password="contraseña-vieja")
    api.post("/api/auth/password-reset/request", json={"email": user.email})
    token = _token_from(outbox)

    first = api.post("/api/auth/password-reset/confirm", json={"token": token, "new_password": "contraseña-nueva"})
    second = api.post("/api/auth/password-reset/confirm", json={"token": token, "new_password": "otra-mas-nueva"})

    assert first.status_code == 200
    assert second.status_code == 400
    db.refresh(user)
    assert verify_password("contraseña-nueva", user.hashed_password)
    login = api.post("/api/auth/login", json={"email": user.email, "password": "contraseña-nueva"})
    assert login.status_code == 200


def test_reset_confirm_rejects_verification_token(api, outbox) -> None:
    api.post("/api/auth/register", json=_register_payload())
    verification_token = _token_from(outbox)

    response = api.post(
        "/api/auth/password-reset/confirm",
        json={"token": verification_token, "new_password": "contraseña-nueva"},
    )

    assert response.status_code == 400


def test_reset_request_is_rate_limited(api) -> None:
    payload = {"email": "no-existe@example.com"}

    codes = [api.post("/api/auth/password-reset/request", json=payload).status_code for _ in range(4)]

    assert codes == [202, 202, 202, 429]


# --- C7: límite de 72 bytes vía HTTP ----------------------------------------


def test_register_rejects_password_over_72_bytes(api, db: Session) -> None:
    payload = {**_register_payload(), "password": "ñ" * 37}

    response = api.post("/api/auth/register", json=payload)

    assert response.status_code == 422
    assert "72 bytes" in response.text
    assert db.query(User).filter_by(email=payload["email"]).first() is None
