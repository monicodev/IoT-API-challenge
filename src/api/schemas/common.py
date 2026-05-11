"""Common Pydantic schemas."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    database: str
    error: str | None = None
