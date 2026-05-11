"""Device service - handles device registry operations."""

from datetime import datetime

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.devices import DeviceInfo
from src.models.event import TelemetryEvent


class DeviceService:
    """Service for handling device registry operations."""

    @staticmethod
    async def list_devices(
        session: AsyncSession,
        since: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[DeviceInfo], int]:
        """
        List devices with pagination and optional filtering by last event time.

        Uses a single query with window functions to get count and results together.
        Returns (devices, total_count).
        """
        from sqlalchemy import and_

        where_clauses = []
        if since:
            where_clauses.append(TelemetryEvent.timestamp >= since)

        count_query = select(func.count(distinct(TelemetryEvent.device_id)))
        if where_clauses:
            count_query = count_query.where(and_(*where_clauses))
        count_result = await session.execute(count_query)
        total = count_result.scalar() or 0

        device_query = select(
            TelemetryEvent.device_id,
            func.max(TelemetryEvent.timestamp).label("last_event_at"),
        )
        if where_clauses:
            device_query = device_query.where(and_(*where_clauses))
        device_query = (
            device_query.group_by(TelemetryEvent.device_id)
            .order_by(func.max(TelemetryEvent.timestamp).desc())
            .limit(limit)
            .offset(offset)
        )

        result = await session.execute(device_query)
        rows = result.fetchall()

        devices = [DeviceInfo(device_id=row[0], last_event_at=row[1]) for row in rows]

        return devices, total

    @staticmethod
    async def get_device_count(
        session: AsyncSession,
        since: datetime | None = None,
    ) -> int:
        """Get total count of active devices."""
        if since:
            result = await session.execute(
                select(func.count(distinct(TelemetryEvent.device_id))).where(
                    TelemetryEvent.timestamp >= since
                )
            )
        else:
            result = await session.execute(
                select(func.count(distinct(TelemetryEvent.device_id)))
            )
        return result.scalar() or 0
