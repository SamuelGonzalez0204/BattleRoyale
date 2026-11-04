"""Fixtures de integración contra un Postgres real.

Se crea (de cero en cada sesión de pytest) la BD `battleroyale_test` en el mismo
servidor que DATABASE_URL, se migra con Alembic hasta head y cada test corre
dentro de una transacción que se deshace al acabar: los `commit()` de los
servicios se convierten en SAVEPOINTs, así que la BD queda limpia entre tests.

TEST_DATABASE_URL permite apuntar a otra BD de pruebas explícitamente.
"""

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.orm import Session

from app.core.config import get_settings

TEST_DB_NAME = "battleroyale_test"
BACKEND_DIR = Path(__file__).resolve().parent.parent


def _test_database_url() -> URL:
    explicit = os.environ.get("TEST_DATABASE_URL")
    if explicit:
        return make_url(explicit)
    return make_url(get_settings().database_url).set(database=TEST_DB_NAME)


def _recreate_database(url: URL) -> None:
    if not url.database or not url.database.endswith("_test"):
        raise RuntimeError(f"Por seguridad la BD de tests debe acabar en '_test': {url.database!r}")
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)'))
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    finally:
        admin.dispose()


def _migrate(url: URL) -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", url.render_as_string(hide_password=False))
    command.upgrade(config, "head")


@pytest.fixture(scope="session")
def db_engine() -> Generator[Engine, None, None]:
    url = _test_database_url()
    _recreate_database(url)
    _migrate(url)
    engine = create_engine(url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def db(db_engine: Engine) -> Generator[Session, None, None]:
    connection = db_engine.connect()
    outer = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint", autoflush=False)
    try:
        yield session
    finally:
        session.close()
        if outer.is_active:
            outer.rollback()
        connection.close()


# --- Fixtures HTTP compartidas (Fase C) -------------------------------------


class RecordingMailBackend:
    """Backend de correo falso: guarda los mensajes en memoria en vez de enviarlos."""

    def __init__(self) -> None:
        self.sent: list = []

    def send(self, message) -> None:
        self.sent.append(message)


@pytest.fixture(autouse=True)
def _reset_rate_limits() -> Generator[None, None, None]:
    # El limitador guarda contadores en memoria a nivel de proceso: cada test empieza limpio.
    from app.core.rate_limit import limiter

    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture()
def outbox() -> RecordingMailBackend:
    return RecordingMailBackend()


@pytest.fixture()
def api(db: Session, outbox: RecordingMailBackend):
    """TestClient con get_db y get_mail_backend sobrescritos (BD de tests + buzón falso)."""
    from fastapi.testclient import TestClient

    from app.db.session import get_db
    from app.main import app
    from app.services.mail import get_mail_backend

    def _override_get_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_mail_backend] = lambda: outbox
    try:
        # Sin `with`: no arranca el lifespan, así el scheduler no toca la BD real.
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def make_user(db: Session):
    """Fábrica de usuarios persistidos. Devuelve (user, cabeceras Authorization)."""
    import uuid

    from app.core.security import create_access_token, hash_password
    from app.models.user import User

    def _make(*, password: str = "contraseña-segura", is_verified: bool = False, chispas: int = 0):
        tag = uuid.uuid4().hex[:10]
        user = User(
            email=f"{tag}@example.com",
            handle=f"u_{tag}",
            hashed_password=hash_password(password),
            is_verified=is_verified,
            chispas=chispas,
        )
        db.add(user)
        db.commit()
        return user, {"Authorization": f"Bearer {create_access_token(str(user.id))}"}

    return _make
