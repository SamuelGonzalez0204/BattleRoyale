from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://battleroyale:battleroyale@db:5432/battleroyale"
    jwt_secret: str = "change-me-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
