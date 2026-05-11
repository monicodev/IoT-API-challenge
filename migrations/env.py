"""Alembic environment configuration."""
import asyncio
import os
from logging.config import fileConfig
from typing import Optional

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.base import Base
from src.models.event import TelemetryEvent

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url_from_env() -> str:
    """Build database URL from environment variables."""
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]

    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "")
    db = os.environ.get("POSTGRES_DB", "iot_telemetry")

    auth = f"{user}:{password}@" if password else f"{user}@"
    return f"postgresql+asyncpg://{auth}{host}:{port}/{db}"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations_with_retry(
    url: str,
    max_retries: int = 10,
    retry_delay: float = 1.0,
) -> None:
    """Run migrations with retry logic for connection resilience."""
    last_error: Optional[Exception] = None

    for attempt in range(max_retries):
        try:
            print(f"[alembic] Connecting to database (attempt {attempt + 1}/{max_retries})...")

            connectable = async_engine_from_config(
                {"sqlalchemy.url": url},
                prefix="sqlalchemy.",
                poolclass=pool.NullPool,
            )

            async with connectable.connect() as connection:
                await connection.run_sync(do_run_migrations)

            await connectable.dispose()
            print("[alembic] Migrations completed successfully")
            return

        except OperationalError as e:
            last_error = e
            err_str = str(e).lower()

            if "gaierror" in err_str or "name resolution" in err_str:
                print(f"[alembic] DNS resolution failed: {e}")
            elif "connection refused" in err_str:
                print(f"[alembic] Connection refused: {e}")
            elif "could not connect" in err_str:
                print(f"[alembic] Could not connect: {e}")
            else:
                print(f"[alembic] Operational error: {e}")

        except OSError as e:
            last_error = e
            print(f"[alembic] OS error (possibly DNS): {e}")

        except Exception as e:
            last_error = e
            print(f"[alembic] Unexpected error: {type(e).__name__} - {e}")

        if attempt < max_retries - 1:
            sleep_time = retry_delay * (2 ** attempt)
            print(f"[alembic] Retrying in {sleep_time:.1f}s...")
            await asyncio.sleep(sleep_time)

    raise RuntimeError(
        f"[alembic] Failed to run migrations after {max_retries} attempts. "
        f"Last error: {last_error}"
    )


async def run_async_migrations() -> None:
    """Run migrations in async mode."""
    url = config.get_main_option("sqlalchemy.url")

    if not url or "driver://" in url or "localhost" in url and "your" in url:
        url = get_database_url_from_env()

    safe_url = url.replace(f"://", "://***:***@") if "@" in url else url
    print(f"[alembic] Using database URL: {safe_url}")

    await run_async_migrations_with_retry(url)


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()