"""Event-related Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class EventCreate(BaseModel):
    """Schema for creating a single telemetry event."""

    device_id: str = Field(..., max_length=255, description="Unique device identifier")
    timestamp: datetime = Field(..., description="Event timestamp in ISO 8601 format")
    metric: str = Field(..., max_length=100, description="Metric name")
    value: float = Field(..., description="Metric value")

    @field_validator("device_id")
    @classmethod
    def validate_device_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("device_id cannot be empty")
        return v.strip()

    @field_validator("metric")
    @classmethod
    def validate_metric(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("metric cannot be empty")
        return v.strip()

    model_config = {"str_strip_whitespace": True}


class EventBatchRequest(BaseModel):
    """Schema for batch event ingestion."""

    events: list[EventCreate] = Field(..., min_length=1, max_length=1000)

    @field_validator("events")
    @classmethod
    def validate_events_not_empty(cls, v: list[EventCreate]) -> list[EventCreate]:
        if not v:
            raise ValueError("events list cannot be empty")
        return v


class EventInsertResponse(BaseModel):
    """Response for event insertion."""

    inserted: int = Field(..., description="Number of events inserted")
    duplicates: int = Field(..., description="Number of duplicate events skipped")
