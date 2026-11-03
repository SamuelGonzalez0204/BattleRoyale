import json
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "change-me-in-prod"
MIN_JWT_SECRET_LENGTH = 32
DEV_HOST_MARKERS = ("localhost", "127.0.0.1", "0.0.0.0")


class ConfigError(RuntimeError):
    """Configuración inválida para el entorno elegido. El arranque debe abortar."""


def parse_cors_origins(raw: str) -> list[str]:
    """Acepta "a,b,c" (lo cómodo en un .env) o una lista JSON '["a","b"]'."""
    text = raw.strip()
    if text.startswith("["):
        return [str(origin).strip() for origin in json.loads(text) if str(origin).strip()]
    return [origin.strip() for origin in text.split(",") if origin.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # "development" (por defecto) o "production": en producción se exige config segura.
    env: Literal["development", "production"] = "development"

    database_url: str = "postgresql+psycopg://battleroyale:battleroyale@db:5432/battleroyale"
    jwt_secret: str = DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    # CORS_ORIGINS se lee como texto (separado por comas o lista JSON) y se expone como lista.
    cors_origins_raw: str = Field(
        default="http://localhost:5173,http://localhost:8080",
        validation_alias="CORS_ORIGINS",
    )

    # El Augurio: cuota objetivo por facción y peso base del azar
    augurio_target_share: float = 1.0 / 3.0
    augurio_base_weight: float = 0.15

    # Rate limiting (slowapi). "memory://" en dev; en prod p. ej. "redis://redis:6379/0".
    rate_limit_enabled: bool = True
    rate_limit_storage_uri: str = "memory://"
    rate_limit_auth: str = "5/minute"
    rate_limit_password_reset: str = "3/minute"
    rate_limit_verification_resend: str = "3/minute"
    rate_limit_reports: str = "10/hour"
    rate_limit_handle_verification: str = "5/hour"
    # Panel de admin: límite generoso, solo para frenar scripts desbocados
    rate_limit_admin: str = "120/minute"

    # Tokens de un solo propósito enviados por email
    email_verification_expire_hours: int = 48
    password_reset_expire_minutes: int = 60

    # Correo: "console" (solo desarrollo, escribe el enlace en el log) o "smtp"
    frontend_base_url: str = "http://localhost:5173"
    mail_backend: str = "console"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "El Ciclo <no-reply@elciclo.local>"
    smtp_starttls: bool = True

    # Economía: máximo de Chispas que una cuenta puede GANAR por día UTC
    chispas_daily_earn_cap: int = 30

    # Logs: nivel del logger raíz (DEBUG, INFO, WARNING...)
    log_level: str = "INFO"

    @property
    def cors_origins(self) -> list[str]:
        return parse_cors_origins(self.cors_origins_raw)


def _is_dev_host(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in DEV_HOST_MARKERS)


def production_config_errors(settings: Settings) -> list[str]:
    """Regla pura: problemas que impiden arrancar en producción ([] si todo está bien)."""
    if settings.env != "production":
        return []
    errors: list[str] = []
    if settings.jwt_secret == DEV_JWT_SECRET or len(settings.jwt_secret) < MIN_JWT_SECRET_LENGTH:
        errors.append(
            f"JWT_SECRET debe ser un secreto propio de al menos {MIN_JWT_SECRET_LENGTH} caracteres "
            "(genera uno con `openssl rand -hex 32`)"
        )
    if not settings.cors_origins or any(_is_dev_host(origin) for origin in settings.cors_origins):
        errors.append("CORS_ORIGINS no puede estar vacío ni contener localhost en producción")
    if settings.mail_backend == "console":
        errors.append("MAIL_BACKEND=console solo vale en desarrollo: usa MAIL_BACKEND=smtp")
    if _is_dev_host(settings.frontend_base_url):
        errors.append("FRONTEND_BASE_URL no puede apuntar a localhost en producción")
    return errors


def ensure_production_ready(settings: Settings) -> None:
    """Falla rápido (ConfigError) listando todos los problemas a la vez."""
    errors = production_config_errors(settings)
    if errors:
        details = "\n".join(f"  - {error}" for error in errors)
        raise ConfigError(f"Configuración inválida para ENV=production:\n{details}")


@lru_cache
def get_settings() -> Settings:
    return Settings()
