# Despliegue — El Ciclo

Guía para poner El Ciclo en producción en un VPS con Docker Compose y Caddy (TLS automático).
Todo el despliegue es **un solo comando** una vez preparado el servidor:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

> Este documento describe el procedimiento; no implica que exista ya un despliegue en marcha.

## Arquitectura

```
Internet ──443/80──▶ caddy ──/api/*──▶ backend:8000 (FastAPI + scheduler)
                          └──resto───▶ frontend:80  (nginx con el build de Vite)
                     backend ──▶ db:5432 (Postgres 16, volumen pgdata, sin puerto publicado)
```

- `docker-compose.prod.yml` es autónomo (no se combina con `docker-compose.yml`).
- Solo Caddy publica puertos (80, 443 y 443/udp para HTTP/3). La BD y el backend solo son accesibles en la red interna de Compose.
- Frontend y API comparten dominio: el frontend se construye con `VITE_API_BASE=https://$DOMAIN` y Caddy enruta `/api/*` al backend.
- El backend arranca con `ENV=production`: si la configuración es insegura, **no arranca** (ver [Validación de arranque](#validación-de-arranque-env-production)).
- Las migraciones de Alembic se aplican solas en cada arranque del backend (`backend/entrypoint.sh`).

## 1. Requisitos

- VPS con Linux (p. ej. Ubuntu 24.04), 1 vCPU / 1–2 GB RAM bastan para empezar.
- Docker Engine y el plugin Compose v2 (`docker compose version`).
- Un dominio propio y una cuenta SMTP (Brevo, Mailgun, SES, Postmark…) para los emails de verificación y recuperación.
- Puertos 80 y 443 abiertos en el firewall (`ufw allow 80,443/tcp && ufw allow 443/udp`).

## 2. DNS

Crea un registro `A` (y `AAAA` si el VPS tiene IPv6) apuntando a la IP del servidor:

```
elciclo.example.com.   A   203.0.113.10
```

Espera a que resuelva (`dig +short elciclo.example.com`) **antes** del primer arranque: Caddy pide el certificado a Let's Encrypt al arrancar y necesita que el dominio ya apunte al VPS.

## 3. Código y `.env`

```bash
git clone https://github.com/SamuelGonzalez0204/BattleRoyale.git /opt/elciclo
cd /opt/elciclo
```

Crea `/opt/elciclo/.env` (está en `.gitignore`; nunca lo subas al repo). Plantilla de producción:

```dotenv
# --- Dominio y TLS (Caddy) ---
DOMAIN=elciclo.example.com
ACME_EMAIL=tu-email@example.com

# --- Postgres ---
POSTGRES_USER=battleroyale
POSTGRES_PASSWORD=<openssl rand -hex 32>
POSTGRES_DB=battleroyale

# --- Backend ---
ENV=production
JWT_SECRET=<openssl rand -hex 32>
CORS_ORIGINS=https://elciclo.example.com
FRONTEND_BASE_URL=https://elciclo.example.com
LOG_LEVEL=INFO

# --- Correo ---
MAIL_BACKEND=smtp
SMTP_HOST=smtp.tu-proveedor.com
SMTP_PORT=587
SMTP_USER=usuario-smtp
SMTP_PASSWORD=contraseña-smtp
SMTP_FROM=El Ciclo <no-reply@elciclo.example.com>
SMTP_STARTTLS=true
```

### Generar secretos

```bash
openssl rand -hex 32   # JWT_SECRET
openssl rand -hex 32   # POSTGRES_PASSWORD
```

Usa valores hexadecimales para `POSTGRES_PASSWORD`: va dentro de `DATABASE_URL` y así no hay caracteres que escapar.
`docker-compose.prod.yml` construye `DATABASE_URL` a partir de `POSTGRES_*`; no hace falta definirla.

Protege el fichero: `chmod 600 .env`.

## 4. Primer despliegue

```bash
cd /opt/elciclo
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs backend --tail 50
```

En los logs del backend (JSON, una línea por evento) deberías ver, en este orden:
`Validando configuración...` → `OK: configuración válida para ENV=production` → `Aplicando migraciones...` → `Running upgrade ...` → el arranque de uvicorn.

Comprueba la salud desde fuera:

```bash
curl -s https://elciclo.example.com/api/health         # {"status":"ok"}  (proceso vivo)
curl -s https://elciclo.example.com/api/health/ready   # {"status":"ok","database":"ok"}  (503 si la BD no responde)
```

### Crear el primer admin

Regístrate con tu cuenta desde la web y después promuévela:

```bash
docker compose -f docker-compose.prod.yml exec backend python -m app.cli make-admin tu-email@example.com
# OK: tu-email@example.com (@tu_handle) ya es admin
```

El panel queda en `https://elciclo.example.com/admin.html` (temporadas y fase, decisión de emergencia, cola de reports y de handles).
La UI solo se muestra a cuentas con `is_admin`; la protección real son los 403 de `/api/admin/*`.

## Validación de arranque (`ENV=production`)

Con `ENV=production` el backend se niega a arrancar (error claro en el log, contenedor reiniciándose) si:

| Problema | Regla |
|---|---|
| `JWT_SECRET` | es el valor de desarrollo (`change-me-in-prod`) o tiene menos de 32 caracteres |
| `CORS_ORIGINS` | está vacío o contiene `localhost` / `127.0.0.1` / `0.0.0.0` |
| `MAIL_BACKEND` | es `console` |
| `FRONTEND_BASE_URL` | apunta a `localhost` |

La comprobación corre antes de las migraciones (`python -m app.cli check-config`) y otra vez al importar la app.
Puedes ejecutarla a mano: `docker compose -f docker-compose.prod.yml run --rm backend python -m app.cli check-config`
(o `... exec backend python -m app.cli check-config` con el servicio en marcha).

## Referencia de variables de entorno

> `.env.example` de la raíz no se ha podido actualizar en esta fase (sin permisos de lectura/escritura sobre ese fichero desde la herramienta), así que esta tabla es la referencia completa.

| Variable | Por defecto (dev) | Descripción |
|---|---|---|
| `ENV` | `development` | `development` o `production` (activa la validación de arranque). |
| `LOG_LEVEL` | `INFO` | Nivel del logger raíz (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `DATABASE_URL` | `postgresql+psycopg://battleroyale:battleroyale@db:5432/battleroyale` | Conexión SQLAlchemy. En prod la construye `docker-compose.prod.yml`. |
| `JWT_SECRET` | `change-me-in-prod` | Secreto HS256 de los JWT. ≥ 32 caracteres en producción. |
| `JWT_ALGORITHM` | `HS256` | Algoritmo JWT. |
| `JWT_EXPIRE_MINUTES` | `10080` (7 días) | Caducidad de la sesión. |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:8080` | Orígenes permitidos, separados por comas (también acepta lista JSON). |
| `AUGURIO_TARGET_SHARE` | `0.3333` | Cuota objetivo por facción del Augurio. |
| `AUGURIO_BASE_WEIGHT` | `0.15` | Peso base del azar en el Augurio. |
| `RATE_LIMIT_ENABLED` | `true` | Activa el rate limiting (slowapi). |
| `RATE_LIMIT_STORAGE_URI` | `memory://` | Almacén de contadores; con varias réplicas usa `redis://...`. |
| `RATE_LIMIT_AUTH` | `5/minute` | Login y registro. |
| `RATE_LIMIT_PASSWORD_RESET` | `3/minute` | Petición de reset de contraseña. |
| `RATE_LIMIT_VERIFICATION_RESEND` | `3/minute` | Reenvío del email de verificación. |
| `RATE_LIMIT_REPORTS` | `10/hour` | Creación de reports. |
| `RATE_LIMIT_HANDLE_VERIFICATION` | `5/hour` | Solicitud de verificación de handle. |
| `RATE_LIMIT_ADMIN` | `120/minute` | Cada endpoint de `/api/admin/*`, por usuario. |
| `RATE_LIMIT_BATTLE_ROYALE` | `30/minute` | Votos de táctica y sello de La Última Luz, y patrocinios (`/api/br/*`, `/api/sponsor`), por usuario. |
| `EMAIL_VERIFICATION_EXPIRE_HOURS` | `48` | Validez del enlace de verificación de email. |
| `PASSWORD_RESET_EXPIRE_MINUTES` | `60` | Validez del enlace de reset. |
| `FRONTEND_BASE_URL` | `http://localhost:5173` | Base de los enlaces que se envían por email. |
| `MAIL_BACKEND` | `console` | `console` (escribe el enlace en el log, solo dev) o `smtp`. |
| `SMTP_HOST` / `SMTP_PORT` | `""` / `587` | Servidor SMTP. |
| `SMTP_USER` / `SMTP_PASSWORD` | `""` | Credenciales SMTP. |
| `SMTP_FROM` | `El Ciclo <no-reply@elciclo.local>` | Remitente. |
| `SMTP_STARTTLS` | `true` | STARTTLS al conectar. |
| `CHISPAS_DAILY_EARN_CAP` | `30` | Máximo de Chispas ganadas por cuenta y día UTC. |
| `FORWARDED_ALLOW_IPS` | (uvicorn: `127.0.0.1`) | IPs de proxy en las que confiar para `X-Forwarded-For`. En prod `*` (solo Caddy llega al backend), así el rate limit ve la IP real. |
| `VITE_API_BASE` (build del frontend) | `http://localhost:8000` | Base de la API. En prod `https://$DOMAIN`. |
| `DOMAIN` / `ACME_EMAIL` (Caddy) | — | Dominio servido y email para Let's Encrypt. |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `battleroyale` | Credenciales de la BD. |

En desarrollo, `docker-compose.yml` pasa todas estas variables al backend con valores por defecto de dev; puedes sobrescribirlas en el `.env` local.

## 5. Logs

El backend escribe logs JSON en stdout (una línea por evento: `ts`, `level`, `logger`, `msg`, y `request_id`, `method`, `path`, `status`, `duration_ms` en las peticiones). Nunca registra cabeceras `Authorization`, tokens, contraseñas ni cuerpos; las rutas se registran sin query string.
Cada respuesta lleva `X-Request-ID` (se respeta el que envíe el cliente si es seguro: `[A-Za-z0-9._-]{1,64}`).

```bash
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs backend --since 1h | grep '"status": 5'
docker compose -f docker-compose.prod.yml logs backend | grep '<request-id>'   # seguir una petición
docker compose -f docker-compose.prod.yml logs -f caddy
```

Docker rota los logs (`json-file`, 5 × 10 MB por servicio).

## 6. Backups de Postgres

Volcado lógico con `pg_dump` desde el contenedor de la BD (no requiere parar nada):

```bash
mkdir -p /opt/elciclo/backups
docker compose -f /opt/elciclo/docker-compose.prod.yml exec -T db \
  sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' \
  > /opt/elciclo/backups/elciclo-$(date +%F).dump
```

Cron diario a las 03:30 con retención de 14 días (`crontab -e` del usuario que ejecuta Docker):

```cron
30 3 * * * cd /opt/elciclo && docker compose -f docker-compose.prod.yml exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' > backups/elciclo-$(date +\%F).dump && find backups -name 'elciclo-*.dump' -mtime +14 -delete
```

(En crontab `%` se escapa como `\%`.) Copia los volcados fuera del VPS (rclone/restic a S3, B2…): un backup en el mismo disco no protege de perder el servidor.

Restaurar:

```bash
docker compose -f docker-compose.prod.yml stop backend
docker compose -f docker-compose.prod.yml exec -T db \
  sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists' \
  < backups/elciclo-AAAA-MM-DD.dump
docker compose -f docker-compose.prod.yml start backend
```

## 7. Actualizar

```bash
cd /opt/elciclo
git pull
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml logs backend --tail 30   # migraciones aplicadas y API arriba
docker image prune -f
```

Las migraciones nuevas se aplican solas al arrancar el backend. Haz un backup antes de actualizar si la versión trae migraciones.

## 8. Problemas frecuentes

- **El backend se reinicia en bucle** → `logs backend`: casi siempre es la validación de `ENV=production` (el mensaje lista cada variable a corregir).
- **Caddy no obtiene certificado** → el DNS aún no apunta al VPS o el puerto 80 está cerrado.
- **CORS en el navegador** → `CORS_ORIGINS` debe ser exactamente `https://$DOMAIN` (sin barra final).
- **Todos los usuarios comparten rate limit** → falta `FORWARDED_ALLOW_IPS` en el backend (ya viene en `docker-compose.prod.yml`).
- **El scheduler** (decisión diaria 00:05 UTC, cierre 23:59 UTC) corre dentro del backend: mantén **una sola réplica** del backend, o se duplicarían los jobs (son idempotentes, pero no está pensado para varias).

## Alternativa: Fly.io

Si no quieres gestionar un VPS: crea dos apps (`fly launch` en `backend/` y en `frontend/`) más una Postgres gestionada (`fly postgres create` + `fly postgres attach`, que define `DATABASE_URL`; cámbiale el esquema a `postgresql+psycopg://`).
Los secretos van con `fly secrets set ENV=production JWT_SECRET=... CORS_ORIGINS=https://<frontend>.fly.dev FRONTEND_BASE_URL=... MAIL_BACKEND=smtp SMTP_...`; el frontend se construye con `--build-arg VITE_API_BASE=https://<backend>.fly.dev`.
Fly termina TLS por ti, así que Caddy sobra. Mantén `min_machines_running = 1` y una sola máquina en el backend para que el scheduler no se duplique ni se duerma.
