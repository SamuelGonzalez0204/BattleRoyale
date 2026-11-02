import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import augurio, auth, decisions, factions, users, world
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.daily_decision import ensure_decision_for_today
from app.services.season import get_active_season

settings = get_settings()
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(
        generate_daily_decision_job,
        CronTrigger(hour=0, minute=5),
        id="daily_decision",
        replace_existing=True,
    )
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="El Ciclo — API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(augurio.router)
app.include_router(factions.router)
app.include_router(world.router)
app.include_router(decisions.router)


@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
