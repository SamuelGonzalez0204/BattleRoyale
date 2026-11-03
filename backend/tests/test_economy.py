"""Economía de Chispas: tope diario (función pura) y bloqueo a cuentas sin verificar."""

from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app.models.chispa import ChispaTransaction
from app.services.economy import (
    award_chispas,
    capped_award,
    chispas_earned_today,
    spend_chispas,
    utc_day_start,
)


@pytest.mark.parametrize(
    ("requested", "earned_today", "cap", "expected"),
    [
        (10, 0, 30, 10),
        (10, 25, 30, 5),
        (10, 30, 30, 0),
        (10, 45, 30, 0),  # ya pasado el tope (p. ej. si se bajó el tope)
        (0, 0, 30, 0),
    ],
)
def test_capped_award(requested: int, earned_today: int, cap: int, expected: int) -> None:
    assert capped_award(requested, earned_today, cap) == expected


def test_utc_day_start_truncates_to_midnight_utc() -> None:
    now = datetime(2026, 11, 3, 17, 45, 12, tzinfo=timezone.utc)

    assert utc_day_start(now) == datetime(2026, 11, 3, tzinfo=timezone.utc)


@pytest.mark.integration
def test_unverified_user_earns_nothing(db: Session, make_user) -> None:
    user, _ = make_user(is_verified=False)

    awarded = award_chispas(db, user, 10, reason="test")
    db.commit()

    assert awarded == 0
    assert user.chispas == 0
    assert db.query(ChispaTransaction).filter_by(user_id=user.id).count() == 0


@pytest.mark.integration
def test_verified_user_earns_up_to_daily_cap(db: Session, make_user) -> None:
    user, _ = make_user(is_verified=True)

    first = award_chispas(db, user, 20, reason="test", daily_cap=30)
    second = award_chispas(db, user, 20, reason="test", daily_cap=30)
    third = award_chispas(db, user, 20, reason="test", daily_cap=30)
    db.commit()

    assert (first, second, third) == (20, 10, 0)
    assert user.chispas == 30
    assert chispas_earned_today(db, user.id) == 30


@pytest.mark.integration
def test_spending_does_not_free_up_daily_cap(db: Session, make_user) -> None:
    user, _ = make_user(is_verified=True)

    award_chispas(db, user, 30, reason="test", daily_cap=30)
    spend_chispas(db, user, 15, reason="gasto")
    again = award_chispas(db, user, 5, reason="test", daily_cap=30)

    assert again == 0
    assert user.chispas == 15
