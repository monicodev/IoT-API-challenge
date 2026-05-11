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

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "ubuntu"
    postgres_password: str = ""
    postgres_db: str = "iot_telemetry"

    class Config:
        env_file = ".env"
        case_sensitive = False

    def get_database_url(self) -> str:
        """Build database URL from settings."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()

# Async engine with NullPool for serverless/short-lived connections
# Use environment DATABASE_URL if available, otherwise build from components
_engine_url = settings.get_database_url()
engine: AsyncEngine = create_async_engine(
    _engine_url,
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


async def check_database_connection(timeout: float = 5.0) -> tuple[bool, str]:
    """
    Check database connectivity with timeout.

    Args:
        timeout: Maximum seconds to wait for connection check.

    Returns:
        Tuple of (is_connected, error_message)
    """
    try:
        async with engine.connect().execution_options(
            timeout=timeout
        ) as conn:
            await conn.execute(text("SELECT 1"))
        return True, ""
    except Exception as e:
        return False, str(e)