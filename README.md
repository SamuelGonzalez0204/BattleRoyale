# El Ciclo — BattleRoyale

Backend del videojuego narrativo persistente: el Augurio, el poblado con sus 5 stats, las tres facciones y la decisión diaria. Es la primera versión funcional del sistema descrito en el plan de diseño — no la ilustración completa del mockup (eso llega después, como capa visual sobre esta API).

Lo que falta por construir, priorizado, está en [`ROADMAP.md`](./ROADMAP.md).

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
  poblado.html    HUD: poblado ilustrado, facciones, Chispas, decisión del día
  src/            JS compartido (api.js, village.js, estilos)
  public/sprites/ sprites CC0 (Kenney) que dibujan el poblado
```

### El poblado ilustrado

`src/village.js` traduce las 5 stats de `/api/world` en una escena con sprites reales (CC0, Kenney): el lago es una textura de agua, los cultivos son tierra labrada con plantas si `comida` lo permite, las casas se van "construyendo" según `poblacion` (de 1 a 5) y los árboles según `defensa` — el resto queda como parcela vacía marcada con un borde punteado. Es la misma lógica que el mockup de diseño, ahora con datos reales en vez de números fijos.

## Qué hace ya la API

| Endpoint | Qué hace |
| --- | --- |
| `POST /api/auth/register` / `/login` | Alta y login, devuelve JWT |
| `GET /api/users/me` | Perfil, facción, rol, Chispas |
| `POST /api/augurio/assign` | Asigna facción con el algoritmo de balanceo oculto (ver `services/sorting.py`) |
| `GET /api/factions` | Las 3 facciones con nº de miembros e influencia % |
| `GET /api/world` | Las 5 stats del mundo de la temporada activa |
| `GET /api/decisions/today` / `POST /today/vote` | La decisión diaria y el voto (con peso extra pagado en Chispas) |

### Decisión diaria automática

Un job (`APScheduler`, corre dentro del propio proceso de la API) genera la decisión del día a las 00:05 UTC a partir de un banco de preguntas (`decision_templates`, migración `0003`) que se recicla cuando se agota. Es idempotente y tiene un **fallback perezoso**: si el job no llegó a correr (contenedor reiniciado a medianoche, etc.), la primera visita a `GET /api/decisions/today` ese día la crea igual — nunca depende solo del cron.

El algoritmo del Augurio está separado en una función pura (`compute_weights`) justo para poder testearlo sin base de datos — ver `backend/tests/test_sorting.py`.

## Tests

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest
```
