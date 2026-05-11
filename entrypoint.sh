#!/bin/bash
set -e

DB_HOST="${POSTGRES_HOST:-postgres}"
DB_PORT="${POSTGRES_PORT:-5432}"
MAX_ATTEMPTS=30
ATTEMPT=0

echo "[entrypoint] Waiting for postgres at ${DB_HOST}:${DB_PORT}..."

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if nc -zv "$DB_HOST" "$DB_PORT" > /dev/null 2>&1; then
        echo "[entrypoint] postgres is reachable"
        break
    fi

    ATTEMPT=$((ATTEMPT + 1))
    echo "[entrypoint] attempt $ATTEMPT/$MAX_ATTEMPTS..."
    sleep 1

    if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
        echo "[entrypoint] ERROR: postgres not reachable after $MAX_ATTEMPTS attempts"
        exit 1
    fi
done

echo "[entrypoint] Running migrations..."
export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${DB_HOST}:${DB_PORT}/${POSTGRES_DB}}"
alembic upgrade head && echo "[entrypoint] Migrations done"

echo "[entrypoint] Starting server..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000