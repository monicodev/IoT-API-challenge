"""Aggregation-related Pydantic schemas."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class AggregationType(StrEnum):
    """Supported aggregation functions."""

    AVG = "avg"
    MIN = "min"
    MAX = "max"
    SUM = "sum"
    COUNT = "count"


class IntervalType(StrEnum):
    """Supported time intervals."""

    MINUTE = "1m"
    FIVE_MINUTES = "5m"
    HOUR = "1h"
    DAY = "1d"


class AggregateQueryParams(BaseModel):
    """Query parameters for aggregation endpoint."""

    device_id: str = Field(..., description="Device identifier")
    metric: str = Field(..., description="Metric name")
    from_time: datetime = Field(..., alias="from", description="Start timestamp")
    to: datetime = Field(..., description="End timestamp")
    interval: IntervalType = Field(
        default=IntervalType.HOUR, description="Aggregation interval"
    )
    aggregation: AggregationType = Field(
        default=AggregationType.AVG, description="Aggregation function"
    )

    model_config = {"populate_by_name": True}


class AggregateDataPoint(BaseModel):
    """Single aggregation data point."""

    timestamp: datetime
    value: float


class AggregateResponse(BaseModel):
    """Response for aggregation query."""

    device_id: str
    metric: str
    interval: str
    aggregation: str
    data: list[AggregateDataPoint]
