"""Devices API route - handles device registry."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.database import get_db
from src.api.schemas.devices import DeviceListResponse
from src.services.device_service import DeviceService

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("", response_model=DeviceListResponse)
async def list_devices(
    since: Optional[datetime] = Query(None, description="Filter devices active since this time"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of devices to return"),
    offset: int = Query(0, ge=0, description="Number of devices to skip"),
    session: AsyncSession = Depends(get_db),
) -> DeviceListResponse:
    """
    List active devices with pagination.

    Returns devices that have sent events, optionally filtered by activity time.
    Includes the timestamp of each device's last event.
    """
    devices, total = await DeviceService.list_devices(
        session=session,
        since=since,
        limit=limit,
        offset=offset,
    )

    return DeviceListResponse(
        devices=devices,
        total=total,
        limit=limit,
        offset=offset,
    )