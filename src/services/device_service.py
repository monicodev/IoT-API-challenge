"""Device service - handles device registry operations."""
from datetime import datetime
from typing import List, Tuple, Optional

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.event import TelemetryEvent
from src.api.schemas.devices import DeviceInfo


class DeviceService:
    """Service for handling device registry operations."""

    @staticmethod
    async def list_devices(
        session: AsyncSession,
        since: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[DeviceInfo], int]:
        """
        List devices with pagination and optional filtering by last event time.

        Uses a single query with window functions to get count and results together.
        Returns (devices, total_count).
        """
        if since:
            base_filter = TelemetryEvent.timestamp >= since
        else:
            base_filter = True

        count_query = select(func.count(distinct(TelemetryEvent.device_id))).where(base_filter)
        count_result = await session.execute(count_query)
        total = count_result.scalar() or 0

        device_query = (
            select(
                TelemetryEvent.device_id,
                func.max(TelemetryEvent.timestamp).label("last_event_at"),
            )
            .where(base_filter)
            .group_by(TelemetryEvent.device_id)
            .order_by(func.max(TelemetryEvent.timestamp).desc())
            .limit(limit)
            .offset(offset)
        )

        result = await session.execute(device_query)
        rows = result.fetchall()

        devices = [
            DeviceInfo(device_id=row[0], last_event_at=row[1])
            for row in rows
        ]

        return devices, total

    @staticmethod
    async def get_device_count(
        session: AsyncSession,
        since: Optional[datetime] = None,
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