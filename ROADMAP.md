# Plan de acción — qué falta por implementar

Estado a fecha de este commit: hay un backend FastAPI + Postgres funcionando (auth, Augurio, facciones, stats del mundo, decisión diaria automática) y un frontend Vite funcional con el poblado ilustrado. Lo que sigue es la lista priorizada de lo que falta para que "El Ciclo" sea el juego completo descrito en el diseño, no solo el esqueleto.

## Fase A — Cerrar el bucle de juego (crítico, bloquea todo lo demás)

Esto es lo más urgente: ahora mismo se puede votar, pero el voto **no cambia nada** en el mundo. Sin esto no hay juego todavía, solo una encuesta.

- [ ] **Aplicar el resultado de la decisión diaria a las stats del mundo.** Al cerrar una decisión (cron a medianoche, o al abrir la siguiente), sumar/restar a `poblacion` / `comida` / `moral` / `defensa` / `oro` según qué opción ganó. Cada `DecisionTemplate` necesita metadatos de efecto (ej. `effect_stat`, `effect_winner`, `effect_loser`) en vez de ser solo texto.
- [ ] **Job de cierre diario**, además del de apertura: a las 23:59 calcula el ganador de la decisión del día, aplica el efecto, y deja el `WorldState` listo para el día siguiente.
- [ ] **Transición de fases de temporada** (`construccion → conflicto → convergencia → colapso`): reglas de cuándo avanza (por semana transcurrida, o por umbral de stats) y quién la dispara (job, no manual).
- [ ] **Asignación de roles** (`mercader` / `guardia` / `cronista` / `explorador`): el campo ya existe en `User` pero nada lo rellena. Definir el criterio (tipo de decisiones en las que vota, o asignación manual al principio) e implementarlo.

## Fase B — La Última Luz (battle royale) y el reset de temporada

Hoy esto solo existe en el mockup de diseño (`BattleRoyale.dc.html`), no en la API.

- [ ] Modelos: `BattleRoyaleEvent` (temporada, fase del evento, zona actual), `Champion` (uno por facción, vinculado a un `User` apadrinado), `Duel` (campeones enfrentados, táctica ganadora).
- [ ] Endpoint para proponer/votar la táctica de cada duelo (reutilizando el patrón de `votes` ya existente).
- [ ] Lógica de eliminación: qué facción pierde la zona cuando baja su participación/votos.
- [ ] **Reset de temporada**: al terminar la Última Luz, crear la `Season` siguiente, reiniciar `WorldState`, aplicar el "sello" que eligió la facción ganadora (bonus inicial, stat más alta, etc. — ver el documento de diseño original).
- [ ] Frontend: página `battle-royale.html` equivalente a `poblado.html`, consumiendo esos endpoints nuevos.
- [ ] Personajes apadrinados: endpoint para que un usuario gaste Chispas en "apadrinar" un personaje (el campo ya está pensado en el diseño, falta modelo + endpoint).

## Fase C — Identidad, confianza y anti-abuso

Ahora mismo cualquiera puede registrarse con cualquier `handle` sin verificarlo, y no hay ningún tope aparte del límite de 50 Chispas por voto.

- [ ] Verificación de handle de IG/TikTok (aunque sea el método manual descrito en el plan de diseño: código temporal en la bio).
- [ ] Verificación de email (confirmación por correo) y flujo de reseteo de contraseña.
- [ ] Tope de Chispas ganables por cuenta y por día (no solo por voto suelto).
- [ ] Rate limiting / anti-bot en `POST /api/auth/register` (ej. `slowapi` + Redis, o un captcha en el frontend).
- [ ] Endpoint de "reportar cuenta sospechosa" + un panel mínimo de moderación para revisarlas.

## Fase D — Operación (para que esto se pueda desplegar de verdad)

- [ ] **CI**: GitHub Actions que corra `pytest` (backend) y `npm run build` (frontend) en cada push/PR — ahora mismo esa verificación la hago yo a mano en cada entrega.
- [ ] **Despliegue**: elegir dónde vive esto en producción (Railway / Fly.io / un VPS con Docker Compose) y documentar el proceso; `JWT_SECRET` y las credenciales de Postgres de `.env.example` son de desarrollo, no vale subirlas tal cual.
- [ ] **Panel de admin**: crear/gestionar temporadas y decisiones manuales de emergencia (una crisis puntual que no viene del banco de plantillas) sin tener que tocar la base de datos a mano.
- [ ] Logging estructurado y algo de observabilidad básica (al menos logs de errores accesibles; métricas si se complica).
- [ ] CORS de producción: `cors_origins` en `config.py` sigue apuntando a `localhost`.

## Fase E — Contenido y frontend

- [ ] **Más preguntas en el banco de decisiones.** Solo hay 8 plantillas (`0003_decision_templates.py`); con una decisión diaria se reciclan cada 8 días, que se va a notar. Hace falta un banco mucho más grande, idealmente con tono específico por fase de temporada.
- [ ] Página de ranking de Chispas (ya referenciada en el nav de `poblado.html`, pero el enlace no lleva a ningún sitio todavía).
- [ ] Página de lore/wiki pública (lo que el plan de diseño llamaba la "capa meta fuera del vídeo").
- [ ] Pulido general del frontend: estados de carga, manejo de errores más claro que `alert()`, accesibilidad, comprobar en móvil.
- [ ] Si el frontend crece mucho más, valorar migrar de HTML+JS suelto a un framework (no es necesario ahora, el proyecto es todavía pequeño).

## Orden sugerido

A (bucle de juego) → C (lo mínimo de identidad/anti-abuso, antes de tener usuarios reales) → D (CI al menos, antes de que el repo crezca más) → B (Última Luz, la pieza más grande) → E (contenido y pulido, en paralelo según haga falta).
