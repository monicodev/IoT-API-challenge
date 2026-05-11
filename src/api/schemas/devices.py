"""Device-related Pydantic schemas."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class DeviceInfo(BaseModel):
    """Device information with last event timestamp."""
    device_id: str
    last_event_at: Optional[datetime] = None


class DeviceListResponse(BaseModel):
    """Response for device list query."""
    devices: List[DeviceInfo]
    total: int = Field(..., description="Total number of devices")
    limit: int = Field(..., description="Limit used")
    offset: int = Field(..., description="Offset used")