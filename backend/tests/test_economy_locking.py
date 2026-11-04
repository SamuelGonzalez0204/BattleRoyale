"""spend_chispas bloquea la fila del usuario (SELECT ... FOR UPDATE) y decide con el
saldo leído bajo ese bloqueo, no con el objeto en memoria (que puede estar viejo)."""

import pytest
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from app.models.chispa import ChispaTransaction
from app.models.user import User
from app.services.economy import InsufficientChispas, spend_chispas
from tests.br_support import member

pytestmark = pytest.mark.integration


def test_two_sequential_spends_cannot_go_negative(db: Session) -> None:
    user, _ = member(db, None, chispas=10)

    spend_chispas(db, user, 6, reason="prueba")
    with pytest.raises(InsufficientChispas):
        spend_chispas(db, user, 6, reason="prueba")
    db.commit()

    db.expire_all()
    assert db.get(User, user.id).chispas == 4
    assert [t.amount for t in db.query(ChispaTransaction).filter(ChispaTransaction.user_id == user.id)] == [-6]


def test_balance_is_read_under_the_lock_not_from_a_stale_object(db: Session) -> None:
    user, _ = member(db, None, chispas=10)
    # Otra petición ya gastó: en BD quedan 2, pero el objeto en memoria aún dice 10.
    db.execute(text("UPDATE users SET chispas = 2 WHERE id = :id"), {"id": user.id})
    assert user.chispas == 10

    with pytest.raises(InsufficientChispas):
        spend_chispas(db, user, 5, reason="prueba")
    assert user.chispas == 2


def test_spend_locks_the_user_row_with_for_update(db: Session) -> None:
    user, _ = member(db, None, chispas=10)
    statements: list[str] = []

    def _capture(conn, cursor, statement, parameters, context, executemany) -> None:
        statements.append(statement)

    engine = db.get_bind().engine
    event.listen(engine, "before_cursor_execute", _capture)
    try:
        spend_chispas(db, user, 3, reason="prueba")
    finally:
        event.remove(engine, "before_cursor_execute", _capture)

    locking = [s for s in statements if "FROM users" in s and "FOR UPDATE" in s]
    assert locking, statements
    assert user.chispas == 7
