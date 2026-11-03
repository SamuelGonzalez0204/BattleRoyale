"""Logs estructurados en JSON (una línea por evento) y X-Request-ID por petición.

Nunca se registran cabeceras Authorization, tokens, contraseñas ni cuerpos:
el middleware solo anota método, ruta (sin query string), status y duración.
"""

import json
import logging
import re
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"
# Solo se acepta un X-Request-ID entrante "inocuo"; si no, se genera uno nuevo.
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
# Campos `extra=` que el formateador copia al JSON. Lista cerrada: nada más se filtra.
EXTRA_FIELDS: tuple[str, ...] = ("method", "path", "status", "duration_ms")
UVICORN_LOGGERS: tuple[str, ...] = ("uvicorn", "uvicorn.error")
# El access log de uvicorn duplicaría (y con IP:puerto) lo que ya registra RequestContextMiddleware.
UVICORN_ACCESS_LOGGER = "uvicorn.access"

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
request_logger = logging.getLogger("el_ciclo.request")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": _iso_utc(record.created),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        request_id = request_id_var.get()
        if request_id:
            payload["request_id"] = request_id
        for field in EXTRA_FIELDS:
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def _iso_utc(created: float) -> str:
    moment = datetime.fromtimestamp(created, tz=timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def configure_logging(level: str = "INFO") -> None:
    """Un único handler JSON en el logger raíz; uvicorn propaga a él (sin formato propio)
    y su access log queda desactivado."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    for name in UVICORN_LOGGERS:
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True
    access_logger = logging.getLogger(UVICORN_ACCESS_LOGGER)
    access_logger.handlers = []
    access_logger.propagate = False


def resolve_request_id(incoming: str | None) -> str:
    if incoming and _VALID_REQUEST_ID.match(incoming):
        return incoming
    return uuid.uuid4().hex


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Asigna/propaga X-Request-ID y registra una línea por petición."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = resolve_request_id(request.headers.get(REQUEST_ID_HEADER))
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            _log_request(request, status_code, started)
            request_id_var.reset(token)


def _log_request(request: Request, status_code: int, started: float) -> None:
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    level = logging.ERROR if status_code >= 500 else logging.INFO
    request_logger.log(
        level,
        "%s %s %s",
        request.method,
        request.url.path,
        status_code,
        extra={
            "method": request.method,
            "path": request.url.path,
            "status": status_code,
            "duration_ms": duration_ms,
        },
    )
