"""D5: logs JSON y X-Request-ID."""

import json
import logging

from app.core.logging import JsonFormatter, request_id_var


def _record(msg: str = "hola %s", args: tuple = ("mundo",), **extra) -> logging.LogRecord:
    record = logging.LogRecord("el_ciclo.test", logging.INFO, __file__, 1, msg, args, None)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_json_formatter_emits_the_base_fields() -> None:
    payload = json.loads(JsonFormatter().format(_record()))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "el_ciclo.test"
    assert payload["msg"] == "hola mundo"
    assert payload["ts"].endswith("Z")
    assert "request_id" not in payload


def test_json_formatter_includes_request_id_from_context() -> None:
    token = request_id_var.set("abc-123")
    try:
        payload = json.loads(JsonFormatter().format(_record()))
    finally:
        request_id_var.reset(token)

    assert payload["request_id"] == "abc-123"


def test_json_formatter_only_includes_whitelisted_extras() -> None:
    record = _record(method="GET", status=200, duration_ms=1.5, password="secreto")

    payload = json.loads(JsonFormatter().format(record))

    assert payload["method"] == "GET"
    assert payload["status"] == 200
    assert payload["duration_ms"] == 1.5
    assert "password" not in payload


def test_json_formatter_serialises_exceptions() -> None:
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        import sys

        record = logging.LogRecord("x", logging.ERROR, __file__, 1, "fallo", (), sys.exc_info())

    payload = json.loads(JsonFormatter().format(record))

    assert "RuntimeError: boom" in payload["exc_info"]


def test_response_carries_a_generated_request_id(api) -> None:
    response = api.get("/api/health")

    assert len(response.headers["X-Request-ID"]) >= 16


def test_valid_incoming_request_id_is_propagated(api) -> None:
    response = api.get("/api/health", headers={"X-Request-ID": "trace-42.a_b"})

    assert response.headers["X-Request-ID"] == "trace-42.a_b"


def test_malformed_incoming_request_id_is_replaced(api) -> None:
    response = api.get("/api/health", headers={"X-Request-ID": "x" * 200})

    assert response.headers["X-Request-ID"] != "x" * 200


def test_request_log_has_method_path_status_and_duration_but_no_secrets(api, make_user, caplog) -> None:
    _, headers = make_user()

    with caplog.at_level(logging.INFO, logger="el_ciclo.request"):
        api.get("/api/users/me?token=secreto", headers=headers)

    records = [r for r in caplog.records if r.name == "el_ciclo.request"]
    assert len(records) == 1
    record = records[0]
    assert (record.method, record.path, record.status) == ("GET", "/api/users/me", 200)
    assert record.duration_ms >= 0
    rendered = JsonFormatter().format(record)
    assert "Bearer" not in rendered
    assert "secreto" not in rendered


def test_configure_logging_routes_uvicorn_to_json_and_silences_its_access_log() -> None:
    from app.core.logging import configure_logging

    configure_logging("INFO")

    root = logging.getLogger()
    assert len(root.handlers) == 1 and isinstance(root.handlers[0].formatter, JsonFormatter)
    assert logging.getLogger("uvicorn.error").propagate is True
    assert logging.getLogger("uvicorn.access").propagate is False
