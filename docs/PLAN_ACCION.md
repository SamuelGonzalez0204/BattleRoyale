# Plan de acción — El Ciclo

Desarrollo concreto de cada fase de [`ROADMAP.md`](../ROADMAP.md). Orden de ejecución: **A → C → D → B**, con **E** en paralelo.
Cada tarea indica los archivos que toca y cómo se verifica.

---

## Fase A — Cerrar el bucle de juego · 1–2 semanas

Objetivo: que el voto diario cambie el mundo y que la temporada avance sola.

| # | Tarea | Archivos | Verificación |
|---|---|---|---|
| A1 | Efectos en las plantillas: columnas `effects_a` / `effects_b` (JSONB, p. ej. `{"comida": 8, "oro": -5}`) en `decision_templates` y `decisions`. Backfill de las 8 plantillas actuales. | `alembic/versions/0004_decision_effects.py`, `models/decision_template.py`, `models/decision.py` | `alembic upgrade head` limpio |
| A2 | Función pura `apply_effects(stats, effects) -> stats` con clamp 0–100. Test primero. | `services/world_effects.py`, `tests/test_world_effects.py` | `pytest` |
| A3 | `close_decision(db, decision)`: ganador por votos ponderados con Chispas, aplica efectos al `WorldState` y marca la decisión `closed`. Idempotente. | `services/daily_decision.py` | Test de integración |
| A4 | Job de cierre a las 23:59 UTC + fallback perezoso: al abrir la decisión de hoy se cierra la de ayer si sigue abierta. | `app/main.py`, `services/daily_decision.py` | Test con reloj simulado |
| A5 | Transición de fase: `advance_phase_if_due(season, now)`, una fase por semana, o adelanto por crisis si una stat llega a 0. La llama el job diario. | `services/season.py` | Test unitario de las reglas |
| A6 | Roles: cada plantilla lleva `role_affinity` (mercader/guardia/cronista/explorador). Tras 5 votos el usuario recibe el rol de la etiqueta que más ha votado; se recalcula en cada cambio de fase. | `services/roles.py`, migración 0004 | Test unitario |
| A7 | Fixture de Postgres para tests de integración (BD `battleroyale_test` en el mismo compose). | `tests/conftest.py` | `pytest` en verde |

**Hecho cuando:** votar un día deja las stats distintas al día siguiente, y una temporada recorre sus 4 fases sin tocar la BD a mano.

---

## Fase C — Identidad y anti-abuso · 1 semana (antes de tener usuarios reales)

| # | Tarea | Archivos |
|---|---|---|
| C1 | Rate limiting en `register` y `login` con `slowapi` (memoria en dev, Redis en prod). | `app/main.py`, `api/routes/auth.py` |
| C2 | Verificación de email: token firmado con caducidad y `GET /api/auth/verify`. Sin verificar no se ganan Chispas. | `core/security.py`, `api/routes/auth.py`, `services/mail.py` |
| C3 | Reset de contraseña con el mismo mecanismo de token. | `api/routes/auth.py` |
| C4 | Tope diario de Chispas por cuenta (suma diaria sobre el ledger de `models/chispa.py`). | `services/economy.py` |
| C5 | Verificación de handle IG/TikTok: código temporal en la bio y revisión manual desde el panel de admin (D4). | `models/user.py`, `api/routes/users.py` |
| C6 | `POST /api/reports` (reportar cuenta) + tabla `reports`. | `models/report.py`, `api/routes/reports.py` |
| C7 | Quitar `passlib` (sin mantenimiento) y usar `bcrypt` directo; limitar la contraseña a 72 bytes en el schema. | `core/security.py`, `schemas/user.py`, `requirements.txt` |

**Hecho cuando:** 20 registros seguidos desde la misma IP devuelven 429, y una cuenta sin email verificado no gana Chispas.

---

## Fase D — Operación · 1 semana

| # | Tarea | Archivos |
|---|---|---|
| D1 | CI: job `backend` (service Postgres + `pytest`) y job `frontend` (`npm ci && npm run build`) en cada push/PR. | `.github/workflows/ci.yml` |
| D2 | Configuración por entorno: `ENV=production` hace fallar el arranque si `JWT_SECRET` o `CORS_ORIGINS` tienen valores de desarrollo. | `core/config.py` |
| D3 | Despliegue: VPS + docker-compose + Caddy (TLS automático). Fly.io queda como alternativa. | `docs/DEPLOY.md`, `docker-compose.prod.yml` |
| D4 | Panel de admin: flag `is_admin` y `/api/admin/*` (temporadas, decisión de emergencia, moderar reports y handles) + `admin.html`. | `api/routes/admin.py`, `frontend/admin.html` |
| D5 | Logs JSON y `/api/health` que también comprueba la BD. | `core/logging.py`, `app/main.py` |

**Hecho cuando:** un PR con un test roto sale en rojo y el despliegue se hace con un solo comando documentado.

---

## Fase B — La Última Luz y el reset · 2–3 semanas

El tablero del battle royale es el mapa **El Valle de la Grieta**: sus 7 regiones son las zonas del evento.

| # | Tarea | Archivos |
|---|---|---|
| B1 | Modelos: `BattleRoyaleEvent` (temporada, ronda, zonas vivas), `Champion` (uno por facción, ligado a un `User`), `Duel`, `TacticVote`, `Sponsorship`. | `models/battle_royale.py`, migración 0005 |
| B2 | Cierre de zonas: en cada ronda la niebla de la Grieta cubre una región, empezando por las de fuera y acabando en las Cumbres Heladas. La facción con menos participación en el duelo de esa zona pierde a su campeón. | `services/battle_royale.py` |
| B3 | Endpoints: `GET /api/br/state`, `POST /api/br/duels/{id}/vote` (mismo patrón que `votes`), `POST /api/sponsor` (gasta Chispas). | `api/routes/battle_royale.py` |
| B4 | Reset: `start_next_season()` crea la `Season` siguiente y reinicia el `WorldState` aplicando el "sello" que elige la facción ganadora. | `services/season.py` |
| B5 | Frontend `battle-royale.html` sobre el visor 3D del mapa: las zonas caídas se cubren de niebla. | `frontend/battle-royale.html`, `frontend/src/map/` |

**Hecho cuando:** una temporada simulada en tests termina con un ganador y abre la Temporada 2 con el sello aplicado.

---

## Fase E — Contenido y frontend · continuo

| # | Tarea |
|---|---|
| E1 | Banco de 60+ plantillas (15 por fase) con campo `region` que las ancla a un lugar del mapa ("El molino de Poniente se ha quedado sin agua…"). |
| E2 | `ranking.html` + `GET /api/ranking`. |
| E3 | `lore.html`: wiki pública generada desde `map-data.json` (regiones, lugares, semillas de historia). |
| E4 | Visor 3D del mapa en `poblado.html`: las stats deciden qué está construido (casas por `poblacion`, campos por `comida`, torres por `defensa`, puestos por `oro`), como hace hoy `village.js` en 2D. |
| E5 | Toasts y estados de carga en lugar de `alert()`; repaso en móvil y accesibilidad. |

---

## El mapa como eje del juego

`map-data.json` (regiones, lugares, pasos disputados) se convierte en fuente de verdad compartida:

- **A:** cada decisión diaria ocurre en una región concreta.
- **B:** las regiones son las zonas que caen en La Última Luz.
- **E:** de él salen la wiki y el poblado 3D.

Los tres **pasos disputados** (Puente del Molino, Camino de las Lápidas, Cala de los Contrabandistas) cambian de bandera según qué facción ganó más decisiones de esa zona. Ahí es donde se generan las historias entre usuarios.
