from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import augurio, auth, decisions, factions, users, world
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="El Ciclo — API", version="0.1.0")

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
