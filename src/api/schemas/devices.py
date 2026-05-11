"""Device-related Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class DeviceInfo(BaseModel):
    """Device information with last event timestamp."""

    device_id: str
    last_event_at: datetime | None = None


class DeviceListResponse(BaseModel):
    """Response for device list query."""

    devices: list[DeviceInfo]
    total: int = Field(..., description="Total number of devices")
    limit: int = Field(..., description="Limit used")
    offset: int = Field(..., description="Offset used")
