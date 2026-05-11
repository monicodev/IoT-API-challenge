"""Integration tests using real PostgreSQL database."""
import os
import pytest
import asyncio
from typing import AsyncGenerator

import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from httpx import AsyncClient, ASGITransport

from src.models.base import Base
from src.models.event import TelemetryEvent
from src.main import app


def _get_connection_params() -> tuple[str, dict]:
    """Parse connection params from DATABASE_URL or env vars."""
    db_name_suffix = "_test"

    if os.environ.get("DATABASE_URL"):
        raw_url = os.environ["DATABASE_URL"]
        if "://" in raw_url:
            proto, rest = raw_url.split("://", 1)
            auth, host_part = rest.split("@", 1)
            user, password = auth.split(":", 1)
            host_port, path_part = host_part.rsplit("/", 1)
            if ":" in host_port:
                host, port = host_port.split(":")
            else:
                host = host_port
                port = "5432"
            test_db_url = f"{proto}://{auth}@{host_port}/{path_part.rsplit('/', 1)[0]}{db_name_suffix}"
            return test_db_url, {"host": host, "port": int(port), "user": user, "password": password}

    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5433")
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "postgres")

    return (
        f"postgresql+asyncpg://{user}:{password}@{host}:{port}/iot_telemetry_test",
        {"host": host, "port": int(port), "user": user, "password": password},
    )


@pytest.fixture(scope="session")
async def setup_database():
    """Setup test database and tables."""
    test_db_url, pg_params = _get_connection_params()

    try:
        conn = await asyncpg.connect(database="postgres", **pg_params)
        db_name = test_db_url.rsplit("/", 1)[-1]
        try:
            await conn.execute(f'CREATE DATABASE {db_name}')
        except asyncpg.exceptions.DuplicateDatabaseError:
            pass
        finally:
            await conn.close()
    except Exception as e:
        print(f"[test] Could not create test database: {e}")

    engine = create_async_engine(
        test_db_url,
        echo=False,
        poolclass=NullPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(setup_database) -> AsyncGenerator[AsyncSession, None]:
    """Provide database session for tests with function scope."""
    engine = setup_database
    async_session_factory = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        yield session


@pytest.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provide HTTP client for API tests with function scope."""
    from src.models import database as db_module

    test_db_url, _ = _get_connection_params()

    engine = create_async_engine(
        test_db_url,
        echo=False,
        poolclass=NullPool,
    )
    async_session_factory = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_db():
        async with async_session_factory() as session:
            yield session

    app.dependency_overrides[db_module.get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()


class TestEventsIntegration:
    """Integration tests for events endpoint."""

    @pytest.mark.asyncio
    async def test_ingest_single_event(self, client: AsyncClient, db_session: AsyncSession):
        """Test ingesting a single event."""
        event_data = {
            "device_id": "device-001",
            "timestamp": "2026-01-15T10:30:00Z",
            "metric": "temperature",
            "value": 23.5,
        }

        response = await client.post("/events", json=event_data)

        assert response.status_code == 201
        data = response.json()
        assert data["inserted"] == 1
        assert data["duplicates"] == 0

        from sqlalchemy import select
        result = await db_session.execute(
            select(TelemetryEvent).where(
                TelemetryEvent.device_id == "device-001",
                TelemetryEvent.metric == "temperature",
            )
        )
        events = result.scalars().all()
        assert len(events) == 1
        assert float(events[0].value) == 23.5

    @pytest.mark.asyncio
    async def test_ingest_batch_events(self, client: AsyncClient):
        """Test ingesting batch events via unified /events endpoint."""
        events_data = [
            {"device_id": "device-002", "timestamp": "2026-01-15T10:30:00Z", "metric": "humidity", "value": 65.0},
            {"device_id": "device-002", "timestamp": "2026-01-15T10:31:00Z", "metric": "humidity", "value": 66.0},
            {"device_id": "device-002", "timestamp": "2026-01-15T10:32:00Z", "metric": "humidity", "value": 67.0},
        ]

        response = await client.post("/events", json=events_data)

        assert response.status_code == 201
        data = response.json()
        assert data["inserted"] == 3
        assert data["duplicates"] == 0

    @pytest.mark.asyncio
    async def test_idempotency_duplicate_event(self, client: AsyncClient):
        """Test idempotency - duplicate event is not inserted."""
        event_data = {
            "device_id": "device-003",
            "timestamp": "2026-01-15T10:30:00Z",
            "metric": "temperature",
            "value": 23.5,
        }

        response1 = await client.post("/events", json=event_data)
        assert response1.status_code == 201
        assert response1.json()["inserted"] == 1

        response2 = await client.post("/events", json=event_data)
        assert response2.status_code == 201
        data = response2.json()
        assert data["inserted"] == 0
        assert data["duplicates"] == 1

    @pytest.mark.asyncio
    async def test_batch_size_validation(self, client: AsyncClient):
        """Test batch size validation - max 1000 events via unified endpoint."""
        events_data = [
            {"device_id": f"device-{i}", "timestamp": "2026-01-15T10:30:00Z", "metric": "temperature", "value": 23.5}
            for i in range(1001)
        ]

        response = await client.post("/events", json=events_data)

        assert response.status_code == 400
        assert "1000" in response.json()["detail"]


class TestAggregateIntegration:
    """Integration tests for aggregate endpoint."""

    @pytest.mark.asyncio
    async def test_aggregate_hourly_avg(self, client: AsyncClient):
        """Test hourly aggregation with avg using UTC datetimes."""
        events = [
            {"device_id": "device-100", "timestamp": "2026-01-15T10:15:00Z", "metric": "temperature", "value": 20.0},
            {"device_id": "device-100", "timestamp": "2026-01-15T10:45:00Z", "metric": "temperature", "value": 30.0},
            {"device_id": "device-100", "timestamp": "2026-01-15T11:15:00Z", "metric": "temperature", "value": 25.0},
            {"device_id": "device-100", "timestamp": "2026-01-15T11:45:00Z", "metric": "temperature", "value": 35.0},
        ]
        await client.post("/events", json=events)

        response = await client.get(
            "/aggregate",
            params={
                "device_id": "device-100",
                "metric": "temperature",
                "from": "2026-01-15T10:00:00Z",
                "to": "2026-01-15T12:00:00Z",
                "interval": "1h",
                "aggregation": "avg",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["device_id"] == "device-100"
        assert data["metric"] == "temperature"
        assert data["interval"] == "1h"
        assert data["aggregation"] == "avg"
        assert len(data["data"]) >= 1

    @pytest.mark.asyncio
    async def test_aggregate_validation_from_before_to(self, client: AsyncClient):
        """Test validation - from must be before to."""
        response = await client.get(
            "/aggregate",
            params={
                "device_id": "device-001",
                "metric": "temperature",
                "from": "2026-01-15T12:00:00Z",
                "to": "2026-01-15T10:00:00Z",
                "interval": "1h",
                "aggregation": "avg",
            },
        )

        assert response.status_code == 400
        assert "before" in response.json()["detail"]


class TestDevicesIntegration:
    """Integration tests for devices endpoint."""

    @pytest.mark.asyncio
    async def test_list_devices(self, client: AsyncClient):
        """Test listing devices."""
        events = [
            {"device_id": "device-200", "timestamp": "2026-01-15T10:30:00Z", "metric": "temperature", "value": 23.5},
            {"device_id": "device-201", "timestamp": "2026-01-15T10:31:00Z", "metric": "temperature", "value": 24.0},
        ]
        await client.post("/events", json=events)

        response = await client.get("/devices")

        assert response.status_code == 200
        data = response.json()
        assert "devices" in data
        assert "total" in data
        assert len(data["devices"]) >= 2

    @pytest.mark.asyncio
    async def test_list_devices_with_pagination(self, client: AsyncClient):
        """Test device list pagination."""
        response = await client.get("/devices?limit=1&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 1
        assert data["offset"] == 0


class TestHealthIntegration:
    """Integration tests for health endpoint."""

    @pytest.mark.asyncio
    async def test_health_check_connected(self, client: AsyncClient):
        """Test health check when database is connected."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"