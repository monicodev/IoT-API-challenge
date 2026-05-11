"""Database configuration and session management."""
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""

    database_url: str = "postgresql+asyncpg://ubuntu@localhost:5432/iot_telemetry"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "ubuntu"
    postgres_password: str = ""
    postgres_db: str = "iot_telemetry"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()


def get_database_url() -> str:
    """Build database URL from settings."""
    return (
        f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )


# Async engine with NullPool for serverless/short-lived connections
engine: AsyncEngine = create_async_engine(
    get_database_url(),
    echo=False,
    poolclass=NullPool,
    future=True,
)

# Async session factory
async_session_factory = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_database_connection() -> tuple[bool, str]:
    """
    Check database connectivity by executing a simple query.

    Returns:
        Tuple of (is_connected, error_message)
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True, ""
    except Exception as e:
        return False, str(e)