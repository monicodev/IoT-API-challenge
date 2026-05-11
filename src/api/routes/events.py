"""Events API route - handles telemetry event ingestion."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.events import (
    EventCreate,
    EventInsertResponse,
)
from src.models.database import get_db
from src.services.event_service import EventService

router = APIRouter(prefix="/events", tags=["events"])


@router.post(
    "", response_model=EventInsertResponse, status_code=status.HTTP_201_CREATED
)
async def ingest_event(
    event_data: EventCreate | list[EventCreate],
    session: AsyncSession = Depends(get_db),
) -> EventInsertResponse:
    """
    Ingest telemetry event(s).

    Accepts either a single event or a list of events (up to 1000).
    Idempotent: duplicate (device_id, timestamp, metric) will be ignored.
    """
    events = event_data if isinstance(event_data, list) else [event_data]

    if len(events) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum batch size is 1000 events",
        )

    inserted, duplicates = await EventService.insert_events_batch(session, events)
    await session.commit()

    return EventInsertResponse(inserted=inserted, duplicates=duplicates)
