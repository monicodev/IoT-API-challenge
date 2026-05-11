"""Integration tests using real PostgreSQL database."""
import pytest
import asyncio
from datetime import datetime, timedelta
from typing import AsyncGenerator

import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient, ASGITransport

from src.models.base import Base
from src.models.event import TelemetryEvent
from src.models.database import get_database_url
from src.main import app
from src.api.schemas.events import EventCreate


# Use a test database
TEST_DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:5433/iot_telemetry_test"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def setup_database():
    """Setup test database and tables."""
    # Connect to PostgreSQL to create test database
    conn = await asyncpg.connect(
        host="localhost",
        port=5433,
        user="postgres",
        password="postgres",
    )

    # Create test database if not exists
    try:
        await conn.execute("CREATE DATABASE iot_telemetry_test")
    except asyncpg.exceptions.DuplicateDatabaseError:
        pass
    await conn.close()

    # Create tables
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def db_session(setup_database) -> AsyncGenerator[AsyncSession, None]:
    """Provide database session for tests."""
    engine = setup_database
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provide HTTP client for API tests."""
    # Override database URL to use test database
    from src.models import database
    original_url = database.settings.database_url
    database.settings.database_url = TEST_DB_URL

    # Recreate engine with test database
    database.engine = create_async_engine(TEST_DB_URL, echo=False)
    database.async_session_factory = sessionmaker(
        database.engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Restore original settings
    database.settings.database_url = original_url
    await database.engine.dispose()


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

        # Verify event was stored
        from sqlalchemy import select
        result = await db_session.execute(
            select(TelemetryEvent).where(
                TelemetryEvent.device_id == "device-001",
                TelemetryEvent.metric == "temperature",
            )
        )
        events = result.fetchall()
        assert len(events) == 1
        assert events[0].value == 23.5

    @pytest.mark.asyncio
    async def test_ingest_batch_events(self, client: AsyncClient):
        """Test ingesting batch events."""
        events_data = {
            "events": [
                {
                    "device_id": "device-002",
                    "timestamp": "2026-01-15T10:30:00Z",
                    "metric": "humidity",
                    "value": 65.0,
                },
                {
                    "device_id": "device-002",
                    "timestamp": "2026-01-15T10:31:00Z",
                    "metric": "humidity",
                    "value": 66.0,
                },
                {
                    "device_id": "device-002",
                    "timestamp": "2026-01-15T10:32:00Z",
                    "metric": "humidity",
                    "value": 67.0,
                },
            ]
        }

        response = await client.post("/events/batch", json=events_data)

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

        # First insertion
        response1 = await client.post("/events", json=event_data)
        assert response1.status_code == 201
        assert response1.json()["inserted"] == 1

        # Duplicate insertion
        response2 = await client.post("/events", json=event_data)
        assert response2.status_code == 201
        data = response2.json()
        assert data["inserted"] == 0
        assert data["duplicates"] == 1

    @pytest.mark.asyncio
    async def test_batch_size_validation(self, client: AsyncClient):
        """Test batch size validation - max 1000."""
        events_data = {
            "events": [
                {
                    "device_id": f"device-{i}",
                    "timestamp": "2026-01-15T10:30:00Z",
                    "metric": "temperature",
                    "value": 23.5,
                }
                for i in range(1001)
            ]
        }

        response = await client.post("/events/batch", json=events_data)

        assert response.status_code == 400
        assert "1000" in response.json()["detail"]


class TestAggregateIntegration:
    """Integration tests for aggregate endpoint."""

    @pytest.mark.asyncio
    async def test_aggregate_hourly_avg(self, client: AsyncClient):
        """Test hourly aggregation with avg."""
        # First insert some events
        events = [
            {"events": [
                {"device_id": "device-100", "timestamp": "2026-01-15T10:15:00Z", "metric": "temperature", "value": 20.0},
                {"device_id": "device-100", "timestamp": "2026-01-15T10:45:00Z", "metric": "temperature", "value": 30.0},
                {"device_id": "device-100", "timestamp": "2026-01-15T11:15:00Z", "metric": "temperature", "value": 25.0},
                {"device_id": "device-100", "timestamp": "2026-01-15T11:45:00Z", "metric": "temperature", "value": 35.0},
            ]}
        ]
        await client.post("/events/batch", json=events[0])

        # Query aggregation
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
        # Insert events for devices
        events = {
            "events": [
                {"device_id": "device-200", "timestamp": "2026-01-15T10:30:00Z", "metric": "temperature", "value": 23.5},
                {"device_id": "device-201", "timestamp": "2026-01-15T10:31:00Z", "metric": "temperature", "value": 24.0},
            ]
        }
        await client.post("/events/batch", json=events)

        # List devices
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