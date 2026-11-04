"""D2: configuración por entorno. Reglas puras, sin BD."""

import pytest

from app.core.config import (
    DEV_JWT_SECRET,
    ConfigError,
    Settings,
    ensure_production_ready,
    parse_cors_origins,
    production_config_errors,
)

STRONG_SECRET = "a" * 64
CONFIG_ENV_VARS = ("ENV", "JWT_SECRET", "CORS_ORIGINS", "MAIL_BACKEND", "FRONTEND_BASE_URL")


@pytest.fixture(autouse=True)
def _hermetic_env(monkeypatch) -> None:
    # El contenedor de dev exporta estas variables; los tests no deben depender de ellas.
    for name in CONFIG_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def _production(**overrides) -> Settings:
    values = {
        "env": "production",
        "jwt_secret": STRONG_SECRET,
        "CORS_ORIGINS": "https://elciclo.example",
        "mail_backend": "smtp",
        "frontend_base_url": "https://elciclo.example",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_parse_cors_origins_accepts_comma_separated_values() -> None:
    assert parse_cors_origins("https://a.example, https://b.example ,") == [
        "https://a.example",
        "https://b.example",
    ]


def test_parse_cors_origins_keeps_accepting_json_lists() -> None:
    assert parse_cors_origins('["https://a.example", "https://b.example"]') == [
        "https://a.example",
        "https://b.example",
    ]


def test_cors_origins_env_var_is_parsed_from_comma_separated(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "https://a.example,https://b.example")

    settings = Settings(_env_file=None)

    assert settings.cors_origins == ["https://a.example", "https://b.example"]


def test_development_is_the_default_and_tolerates_dev_values() -> None:
    settings = Settings(_env_file=None)

    assert settings.env == "development"
    assert production_config_errors(settings) == []
    ensure_production_ready(settings)  # no lanza


def test_valid_production_settings_pass() -> None:
    assert production_config_errors(_production()) == []


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"jwt_secret": DEV_JWT_SECRET}, "JWT_SECRET"),
        ({"jwt_secret": "corto-de-31-caracteres-exactos!"}, "JWT_SECRET"),
        ({"CORS_ORIGINS": "https://ok.example,http://localhost:5173"}, "CORS_ORIGINS"),
        ({"CORS_ORIGINS": "http://127.0.0.1:8080"}, "CORS_ORIGINS"),
        ({"mail_backend": "console"}, "MAIL_BACKEND"),
        ({"frontend_base_url": "http://localhost:5173"}, "FRONTEND_BASE_URL"),
    ],
)
def test_production_rejects_development_values(overrides, fragment) -> None:
    errors = production_config_errors(_production(**overrides))

    assert len(errors) == 1
    assert fragment in errors[0]


def test_ensure_production_ready_lists_every_problem_at_once() -> None:
    settings = _production(jwt_secret=DEV_JWT_SECRET, mail_backend="console")

    with pytest.raises(ConfigError) as exc_info:
        ensure_production_ready(settings)

    message = str(exc_info.value)
    assert "JWT_SECRET" in message
    assert "MAIL_BACKEND" in message


def test_unknown_env_value_is_rejected() -> None:
    with pytest.raises(ValueError):
        Settings(_env_file=None, env="staging")
