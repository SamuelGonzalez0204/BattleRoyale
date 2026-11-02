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


@lru_cache
def get_settings() -> Settings:
    return Settings()
