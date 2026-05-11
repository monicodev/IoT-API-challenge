"""Devices API route - handles device registry."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.devices import DeviceListResponse
from src.models.database import get_db
from src.services.device_service import DeviceService

router = APIRouter(prefix="/devices", tags=["devices"])

DEFAULT_LIMIT: int = 50


@router.get("", response_model=DeviceListResponse)
async def list_devices(
    since: datetime | None = Query(
        None, description="Filter devices active since this time"
    ),
    limit: int = Query(
        DEFAULT_LIMIT, ge=1, le=1000, description="Maximum number of devices to return"
    ),
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
