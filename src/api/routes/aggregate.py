"""Aggregate API route - handles time-based aggregations."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.database import get_db
from src.api.schemas.aggregate import (
    AggregateResponse,
    AggregateDataPoint,
    AggregationType,
    IntervalType,
)
from src.services.aggregation_service import AggregationService

router = APIRouter(prefix="/aggregate", tags=["aggregate"])


@router.get("", response_model=AggregateResponse)
async def get_aggregation(
    device_id: str = Query(..., description="Device identifier"),
    metric: str = Query(..., description="Metric name"),
    from_time: datetime = Query(..., alias="from", description="Start timestamp"),
    to: datetime = Query(..., description="End timestamp"),
    interval: IntervalType = Query(IntervalType.HOUR, description="Aggregation interval"),
    aggregation: AggregationType = Query(AggregationType.AVG, description="Aggregation function"),
    session: AsyncSession = Depends(get_db),
) -> AggregateResponse:
    """
    Get aggregated telemetry data for a device and metric.

    Uses PostgreSQL date_trunc for efficient time-based grouping.
    """
    if from_time >= to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'from' must be before 'to'",
        )

    if (to - from_time).days > 365:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Time range cannot exceed 365 days",
        )

    data_points = await AggregationService.get_aggregation(
        session=session,
        device_id=device_id,
        metric=metric,
        from_time=from_time,
        to=to,
        interval=interval,
        aggregation=aggregation,
    )

    return AggregateResponse(
        device_id=device_id,
        metric=metric,
        interval=interval.value,
        aggregation=aggregation.value,
        data=[
            AggregateDataPoint(timestamp=ts, value=value)
            for ts, value in data_points
        ],
    )