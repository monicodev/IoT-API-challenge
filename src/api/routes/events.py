"""Events API route - handles telemetry event ingestion."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.database import get_db
from src.api.schemas.events import (
    EventCreate,
    EventBatchRequest,
    EventInsertResponse,
)
from src.services.event_service import EventService

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventInsertResponse, status_code=status.HTTP_201_CREATED)
async def ingest_event(
    event: EventCreate,
    session: AsyncSession = Depends(get_db),
) -> EventInsertResponse:
    """
    Ingest a single telemetry event.

    Idempotent: duplicate (device_id, timestamp, metric) will be ignored.
    """
    inserted, duplicates = await EventService.insert_event(session, event)
    await session.commit()
    return EventInsertResponse(inserted=inserted, duplicates=duplicates)


@router.post("/batch", response_model=EventInsertResponse, status_code=status.HTTP_201_CREATED)
async def ingest_events_batch(
    batch: EventBatchRequest,
    session: AsyncSession = Depends(get_db),
) -> EventInsertResponse:
    """
    Ingest multiple telemetry events (up to 1000).

    Idempotent: duplicates based on (device_id, timestamp, metric) will be ignored.
    Uses PostgreSQL ON CONFLICT DO NOTHING for high performance.
    """
    if len(batch.events) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum batch size is 1000 events",
        )

    inserted, duplicates = await EventService.insert_events_batch(session, batch.events)
    return EventInsertResponse(inserted=inserted, duplicates=duplicates)