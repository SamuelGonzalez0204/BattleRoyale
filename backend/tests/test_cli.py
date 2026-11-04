"""D4: CLI `python -m app.cli make-admin <email>`."""

from contextlib import nullcontext

import pytest
from sqlalchemy.orm import Session

from app.cli import main, promote_to_admin

pytestmark = pytest.mark.integration


def test_promote_to_admin_sets_flag_case_insensitively(db: Session, make_user) -> None:
    user, _ = make_user()

    promoted = promote_to_admin(db, user.email.upper())

    assert promoted.id == user.id
    db.refresh(user)
    assert user.is_admin is True


def test_promote_to_admin_unknown_email_raises(db: Session) -> None:
    with pytest.raises(LookupError):
        promote_to_admin(db, "nadie@example.com")


def test_cli_make_admin_reports_success(db: Session, make_user, capsys) -> None:
    user, _ = make_user()

    exit_code = main(["make-admin", user.email], session_factory=lambda: nullcontext(db))

    assert exit_code == 0
    assert user.email in capsys.readouterr().out
    db.refresh(user)
    assert user.is_admin is True


def test_cli_make_admin_unknown_email_exits_with_error(db: Session, capsys) -> None:
    exit_code = main(["make-admin", "nadie@example.com"], session_factory=lambda: nullcontext(db))

    assert exit_code == 1
    assert "nadie@example.com" in capsys.readouterr().err
