"""Rate limiting con slowapi. El almacenamiento sale de settings para poder enchufar
Redis en producción sin tocar código (RATE_LIMIT_STORAGE_URI=redis://...)."""

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import get_settings
from app.core.security import decode_access_token

RATE_LIMITED_DETAIL = "Demasiados intentos. Espera un poco antes de volver a probar."

_settings = get_settings()

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_settings.rate_limit_storage_uri,
    enabled=_settings.rate_limit_enabled,
)


def user_or_ip_key(request: Request) -> str:
    """Clave por usuario autenticado (si el bearer es válido) o, si no, por IP."""
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token:
        subject = decode_access_token(token)
        if subject:
            return f"user:{subject}"
    return f"ip:{get_remote_address(request)}"


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": RATE_LIMITED_DETAIL})
