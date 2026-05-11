"""Device service - handles device registry operations."""
from datetime import datetime
from typing import List, Tuple, Optional

from sqlalchemy import select, func, distinct
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

        Returns (devices, total_count).
        """
        # Base query to get distinct device IDs with their last event timestamp
        if since:
            # Subquery to get devices that have events after 'since'
            last_event_subquery = (
                select(
                    TelemetryEvent.device_id,
                    func.max(TelemetryEvent.timestamp).label("last_event_at")
                )
                .where(TelemetryEvent.timestamp >= since)
                .group_by(TelemetryEvent.device_id)
                .order_by(func.max(TelemetryEvent.timestamp).desc())
                .limit(limit)
                .offset(offset)
                .subquery()
            )

            # Count query
            count_subquery = (
                select(
                    func.count(distinct(TelemetryEvent.device_id))
                )
                .where(TelemetryEvent.timestamp >= since)
                .scalar_subquery()
            )

            # Main query
            query = select(last_event_subquery)
            result = await session.execute(query)
            rows = result.fetchall()

            count_result = await session.execute(
                select(count_subquery)
            )
            total = count_result.scalar() or 0
        else:
            # No filter - get all devices
            last_event_subquery = (
                select(
                    TelemetryEvent.device_id,
                    func.max(TelemetryEvent.timestamp).label("last_event_at")
                )
                .group_by(TelemetryEvent.device_id)
                .order_by(func.max(TelemetryEvent.timestamp).desc())
                .limit(limit)
                .offset(offset)
                .subquery()
            )

            # Count distinct devices
            count_result = await session.execute(
                select(func.count(distinct(TelemetryEvent.device_id)))
            )
            total = count_result.scalar() or 0

            # Main query
            query = select(last_event_subquery)
            result = await session.execute(query)
            rows = result.fetchall()

        devices = [
            DeviceInfo(device_id=row[0], last_event_at=row[1])
            for row in rows
        ]

        return devices, total

    @staticmethod
    async def get_device_count(session: AsyncSession, since: Optional[datetime] = None) -> int:
        """Get total count of active devices."""
        if since:
            result = await session.execute(
                select(func.count(distinct(TelemetryEvent.device_id)))
                .where(TelemetryEvent.timestamp >= since)
            )
        else:
            result = await session.execute(
                select(func.count(distinct(TelemetryEvent.device_id)))
            )
        return result.scalar() or 0