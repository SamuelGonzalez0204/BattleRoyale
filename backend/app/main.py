import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.routes import admin, augurio, auth, decisions, factions, reports, users, world
from app.core.config import ensure_production_ready, get_settings
from app.core.logging import REQUEST_ID_HEADER, RequestContextMiddleware, configure_logging
from app.core.rate_limit import limiter, rate_limit_exceeded_handler
from app.db.session import SessionLocal, get_db
from app.services.daily_cycle import run_daily_close
from app.services.daily_decision import ensure_decision_for_today
from app.services.season import get_active_season

settings = get_settings()
# Fail fast: con ENV=production y valores de desarrollo la API no llega a arrancar.
ensure_production_ready(settings)
configure_logging(settings.log_level)
logger = logging.getLogger("el_ciclo.scheduler")

scheduler = BackgroundScheduler(timezone="UTC")


def generate_daily_decision_job() -> None:
    """Crea la decisión del día para la temporada activa si todavía no existe.
    Es idempotente: también se llama de forma perezosa desde GET /api/decisions/today,
    así que si este job no llega a correr (contenedor caído a medianoche, etc.)
    la primera visita del día la crea igualmente."""
    db = SessionLocal()
    try:
        season = get_active_season(db)
        ensure_decision_for_today(db, season)
    except ValueError:
        logger.info("Sin temporada activa o sin plantillas: no se generó decisión diaria")
    finally:
        db.close()


def close_daily_decision_job() -> None:
    """Cierra la decisión del día (aplica efectos al mundo) y avanza la fase si toca.
    Idempotente; si no corre, GET /api/decisions/today cierra la de ayer al día siguiente."""
    db = SessionLocal()
    try:
        result = run_daily_close(db)
        logger.info(
            "Cierre diario: %d decisiones cerradas, fase=%s (cambio=%s)",
            result.closed_decisions,
            result.phase.value,
            result.phase_changed,
        )
    except ValueError:
        logger.info("Sin temporada activa o sin estado de mundo: no se cerró la decisión diaria")
    except Exception:
        db.rollback()
        logger.exception("Error inesperado en el cierre diario")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(
        generate_daily_decision_job,
        CronTrigger(hour=0, minute=5),
        id="daily_decision",
        replace_existing=True,
    )
    scheduler.add_job(
        close_daily_decision_job,
        CronTrigger(hour=23, minute=59),
        id="daily_close",
        replace_existing=True,
    )
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="El Ciclo — API", version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[REQUEST_ID_HEADER],
)
# Añadido el último = el más externo: también registra preflights CORS y errores 500.
app.add_middleware(RequestContextMiddleware)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(augurio.router)
app.include_router(factions.router)
app.include_router(world.router)
app.include_router(decisions.router)
app.include_router(reports.router)
app.include_router(admin.router)


@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    """Liveness: no toca la BD, responde siempre rápido."""
    return {"status": "ok"}


@app.get("/api/health/ready", tags=["health"])
def ready(db: Session = Depends(get_db)) -> JSONResponse:
    """Readiness: comprueba la BD con SELECT 1 (503 si no responde)."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logging.getLogger("el_ciclo.health").exception("La BD no responde al SELECT 1")
        return JSONResponse(status_code=503, content={"status": "unavailable", "database": "unavailable"})
    return JSONResponse(content={"status": "ok", "database": "ok"})
