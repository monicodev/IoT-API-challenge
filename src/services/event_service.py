"""Event service - handles telemetry event ingestion."""
from datetime import datetime
from typing import List, Tuple

from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.event import TelemetryEvent
from src.api.schemas.events import EventCreate


class EventService:
    """Service for handling telemetry event operations."""

    @staticmethod
    async def insert_event(session: AsyncSession, event: EventCreate) -> Tuple[int, int]:
        """
        Insert a single telemetry event.

        Uses ON CONFLICT DO NOTHING for idempotency.
        Returns (inserted_count, duplicate_count).
        """
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        stmt = pg_insert(TelemetryEvent).values(
            device_id=event.device_id,
            timestamp=event.timestamp,
            metric=event.metric,
            value=event.value,
        ).on_conflict_do_nothing(
            constraint="uq_events_device_timestamp_metric"
        ).returning(TelemetryEvent.id)

        result = await session.execute(stmt)
        inserted = len(result.fetchall())
        await session.commit()
        return inserted, 1 - inserted  # If inserted=1, duplicates=0

    @staticmethod
    async def insert_events_batch(
        session: AsyncSession,
        events: List[EventCreate]
    ) -> Tuple[int, int]:
        """
        Insert multiple telemetry events in batch.

        Uses PostgreSQL ON CONFLICT DO NOTHING via SQLAlchemy for performance.
        Returns (inserted_count, duplicate_count).
        """
        if not events:
            return 0, 0

        from sqlalchemy.dialects.postgresql import insert as pg_insert

        # Prepare values for bulk insert
        values = [
            {
                "device_id": e.device_id,
                "timestamp": e.timestamp,
                "metric": e.metric,
                "value": e.value,
            }
            for e in events
        ]

        # Execute bulk insert with ON CONFLICT DO NOTHING
        stmt = pg_insert(TelemetryEvent).values(values).on_conflict_do_nothing(
            constraint="uq_events_device_timestamp_metric"
        ).returning(TelemetryEvent.id)

        result = await session.execute(stmt)

        inserted = len(result.fetchall())
        duplicates = len(events) - inserted

        await session.commit()

        return inserted, duplicates

    @staticmethod
    async def count_events_by_device(
        session: AsyncSession,
        device_id: str,
        from_time: datetime,
        to: datetime
    ) -> int:
        """Count events for a device within a time range."""
        result = await session.execute(
            select(TelemetryEvent).where(
                TelemetryEvent.device_id == device_id,
                TelemetryEvent.timestamp >= from_time,
                TelemetryEvent.timestamp <= to,
            )
        )
        return len(result.fetchall())