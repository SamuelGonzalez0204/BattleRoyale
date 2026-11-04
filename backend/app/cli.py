"""Comandos de operación. Uso:

    python -m app.cli make-admin <email>   # concede acceso al panel /api/admin
    python -m app.cli check-config         # valida la config del entorno (falla con ENV=production inseguro)

Aquí sí se escribe por stdout/stderr: es la salida del comando.
"""

import argparse
import sys
from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import ConfigError, ensure_production_ready, get_settings
from app.models.user import User

# Devuelve un context manager que entrega una Session (una Session ya lo es: se cierra al salir).
SessionFactory = Callable[[], AbstractContextManager[Session]]


def promote_to_admin(db: Session, email: str) -> User:
    """Marca la cuenta como admin (email sin distinguir mayúsculas). Hace commit."""
    user = db.query(User).filter(func.lower(User.email) == email.strip().lower()).first()
    if user is None:
        raise LookupError(f"No existe ninguna cuenta con el email {email}")
    user.is_admin = True
    db.commit()
    return user


def _make_admin(email: str, session_factory: SessionFactory) -> int:
    with session_factory() as db:
        try:
            user = promote_to_admin(db, email)
        except LookupError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(f"OK: {user.email} (@{user.handle}) ya es admin")
    return 0


def _check_config() -> int:
    settings = get_settings()
    try:
        ensure_production_ready(settings)
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"OK: configuración válida para ENV={settings.env}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="Comandos de operación de El Ciclo")
    commands = parser.add_subparsers(dest="command", required=True)
    make_admin = commands.add_parser("make-admin", help="Concede permisos de admin a una cuenta existente")
    make_admin.add_argument("email")
    commands.add_parser("check-config", help="Valida la configuración del entorno actual")
    return parser


def _default_session_factory() -> Session:
    from app.db.session import SessionLocal

    return SessionLocal()


def main(argv: Sequence[str] | None = None, session_factory: SessionFactory = _default_session_factory) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "make-admin":
        return _make_admin(args.email, session_factory)
    return _check_config()


if __name__ == "__main__":
    sys.exit(main())
