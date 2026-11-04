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
