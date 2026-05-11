"""Common Pydantic schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    database: str
    error: Optional[str] = None