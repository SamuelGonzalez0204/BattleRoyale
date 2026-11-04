#!/bin/sh
set -e

echo "Validando configuración..."
python -m app.cli check-config

echo "Aplicando migraciones..."
alembic upgrade head

echo "Arrancando API..."
# Sin access log de uvicorn: el middleware de la app ya registra cada petición en JSON.
# Tras un proxy (Caddy) define FORWARDED_ALLOW_IPS para que la IP real llegue al rate limit.
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log
