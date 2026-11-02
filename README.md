# El Ciclo — BattleRoyale

Backend del videojuego narrativo persistente: el Augurio, el poblado con sus 5 stats, las tres facciones y la decisión diaria. Es la primera versión funcional del sistema descrito en el plan de diseño — no la ilustración completa del mockup (eso llega después, como capa visual sobre esta API).

## Stack

- **Backend:** Python 3.12 + FastAPI + SQLAlchemy 2 + Alembic
- **Base de datos:** PostgreSQL 16
- **Frontend:** JS vanilla (ES modules) + CSS + Vite, sin framework
- **Todo:** contenedorizado con Docker / docker-compose

## Arrancar en local

```bash
cp .env.example .env
docker compose up --build
```

- API: http://localhost:8000 (docs interactivas en `/docs`)
- Web: http://localhost:5173

El backend aplica las migraciones de Alembic automáticamente al arrancar (`entrypoint.sh`), incluida la semilla de las 3 facciones y la Temporada 1.

## Estructura

```
backend/
  app/
    api/routes/   endpoints REST
    models/       tablas SQLAlchemy
    schemas/      modelos Pydantic de entrada/salida
    services/     lógica de negocio (Augurio, economía de Chispas, temporada)
    core/         config y seguridad (JWT, hashing)
  alembic/        migraciones versionadas
  tests/          pytest (lógica del Augurio probada sin tocar la BD)
frontend/
  index.html      login / registro
  augurio.html    asignación de facción
  poblado.html    HUD: stats del mundo, facciones, Chispas, decisión del día
  src/            JS compartido (api.js, estilos)
```

## Qué hace ya la API

| Endpoint | Qué hace |
| --- | --- |
| `POST /api/auth/register` / `/login` | Alta y login, devuelve JWT |
| `GET /api/users/me` | Perfil, facción, rol, Chispas |
| `POST /api/augurio/assign` | Asigna facción con el algoritmo de balanceo oculto (ver `services/sorting.py`) |
| `GET /api/factions` | Las 3 facciones con nº de miembros e influencia % |
| `GET /api/world` | Las 5 stats del mundo de la temporada activa |
| `GET /api/decisions/today` / `POST /today/vote` | La decisión diaria y el voto (con peso extra pagado en Chispas) |

El algoritmo del Augurio está separado en una función pura (`compute_weights`) justo para poder testearlo sin base de datos — ver `backend/tests/test_sorting.py`.

## Lo que falta a propósito (siguiente iteración)

- **Crear la decisión de cada día** todavía es manual (no hay scheduler ni panel de admin). De momento se inserta a mano en `decisions`.
- **Transición de fases de temporada** (construcción → conflicto → convergencia → colapso) y el **reset/Última Luz** no tienen lógica de backend aún — solo existen en el diseño.
- El **frontend es funcional pero no ilustrado**: usa barras simples, no el poblado con casas/árboles/lago del mockup. Portar esos sprites (Kenney) a esta web real es la siguiente tarea visual.
- No hay verificación real de identidad de Instagram/TikTok todavía (el `handle` se guarda tal cual, sin comprobar que existe).

## Tests

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest
```
