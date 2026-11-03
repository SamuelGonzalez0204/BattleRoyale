"""Unitarios de los schemas de usuario: límite de 72 bytes de bcrypt."""

import pytest
from pydantic import ValidationError

from app.schemas.user import PasswordResetConfirm, UserRegister


def test_password_of_72_bytes_is_accepted() -> None:
    payload = UserRegister(email="a@example.com", handle="ab", password="a" * 72)

    assert len(payload.password) == 72


def test_password_over_72_bytes_is_rejected_with_clear_message() -> None:
    # 37 "ñ" = 74 bytes en UTF-8 aunque solo sean 37 caracteres.
    with pytest.raises(ValidationError) as exc_info:
        UserRegister(email="a@example.com", handle="ab", password="ñ" * 37)

    assert "72 bytes" in str(exc_info.value)


def test_password_reset_confirm_applies_same_rule() -> None:
    with pytest.raises(ValidationError):
        PasswordResetConfirm(token="t", new_password="x" * 73)
    with pytest.raises(ValidationError):
        PasswordResetConfirm(token="t", new_password="corta")
