"""Unit tests for event endpoints and service."""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.api.schemas.events import EventCreate, EventInsertResponse
from src.services.event_service import EventService


class TestEventCreate:
    """Tests for EventCreate schema validation."""

    def test_valid_event(self):
        """Test valid event creation."""
        event = EventCreate(
            device_id="device-001",
            timestamp=datetime(2026, 1, 15, 10, 30, 0),
            metric="temperature",
            value=23.5,
        )
        assert event.device_id == "device-001"
        assert event.metric == "temperature"
        assert event.value == 23.5

    def test_device_id_stripped(self):
        """Test device_id whitespace is stripped."""
        event = EventCreate(
            device_id="  device-001  ",
            timestamp=datetime(2026, 1, 15, 10, 30, 0),
            metric="temperature",
            value=23.5,
        )
        assert event.device_id == "device-001"

    def test_empty_device_id_rejected(self):
        """Test empty device_id is rejected."""
        with pytest.raises(ValueError):
            EventCreate(
                device_id="   ",
                timestamp=datetime(2026, 1, 15, 10, 30, 0),
                metric="temperature",
                value=23.5,
            )

    def test_empty_metric_rejected(self):
        """Test empty metric is rejected."""
        with pytest.raises(ValueError):
            EventCreate(
                device_id="device-001",
                timestamp=datetime(2026, 1, 15, 10, 30, 0),
                metric="   ",
                value=23.5,
            )

    def test_device_id_max_length(self):
        """Test device_id max length validation."""
        with pytest.raises(ValueError):
            EventCreate(
                device_id="a" * 256,
                timestamp=datetime(2026, 1, 15, 10, 30, 0),
                metric="temperature",
                value=23.5,
            )

    def test_metric_max_length(self):
        """Test metric max length validation."""
        with pytest.raises(ValueError):
            EventCreate(
                device_id="device-001",
                timestamp=datetime(2026, 1, 15, 10, 30, 0),
                metric="a" * 101,
                value=23.5,
            )


class TestEventInsertResponse:
    """Tests for EventInsertResponse schema."""

    def test_response_creation(self):
        """Test event insert response creation."""
        response = EventInsertResponse(inserted=5, duplicates=2)
        assert response.inserted == 5
        assert response.duplicates == 2


class TestEventService:
    """Tests for EventService using mocks."""

    @pytest.mark.asyncio
    async def test_insert_event_success(self):
        """Test successful single event insertion."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("uuid-1",)]
        mock_session.execute.return_value = mock_result

        event = EventCreate(
            device_id="device-001",
            timestamp=datetime(2026, 1, 15, 10, 30, 0),
            metric="temperature",
            value=23.5,
        )

        inserted, duplicates = await EventService.insert_event(mock_session, event)

        assert inserted == 1
        assert duplicates == 0
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_insert_event_duplicate(self):
        """Test duplicate event is handled correctly."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        event = EventCreate(
            device_id="device-001",
            timestamp=datetime(2026, 1, 15, 10, 30, 0),
            metric="temperature",
            value=23.5,
        )

        inserted, duplicates = await EventService.insert_event(mock_session, event)

        assert inserted == 0
        assert duplicates == 1

    @pytest.mark.asyncio
    async def test_insert_batch_empty(self):
        """Test empty batch returns zeros."""
        mock_session = AsyncMock()

        inserted, duplicates = await EventService.insert_events_batch(mock_session, [])

        assert inserted == 0
        assert duplicates == 0

    @pytest.mark.asyncio
    async def test_insert_batch_success(self):
        """Test successful batch insertion."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("uuid-1",), ("uuid-2",)]
        mock_session.execute.return_value = mock_result

        events = [
            EventCreate(
                device_id="device-001",
                timestamp=datetime(2026, 1, 15, 10, 30, 0),
                metric="temperature",
                value=23.5,
            ),
            EventCreate(
                device_id="device-001",
                timestamp=datetime(2026, 1, 15, 10, 31, 0),
                metric="temperature",
                value=23.7,
            ),
        ]

        inserted, duplicates = await EventService.insert_events_batch(mock_session, events)

        assert inserted == 2
        assert duplicates == 0

    @pytest.mark.asyncio
    async def test_insert_batch_mixed_new_and_duplicate(self):
        """Test batch insertion with mixed new and duplicate events.

        CRITICAL: This verifies idempotency - when 1 of 3 events is a duplicate,
        the other 2 should still be inserted successfully.
        """
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("uuid-1",), ("uuid-2")]
        mock_session.execute.return_value = mock_result

        events = [
            EventCreate(
                device_id="device-001",
                timestamp=datetime(2026, 1, 15, 10, 30, 0),
                metric="temperature",
                value=23.5,
            ),
            EventCreate(
                device_id="device-001",
                timestamp=datetime(2026, 1, 15, 10, 31, 0),
                metric="temperature",
                value=23.7,
            ),
            EventCreate(
                device_id="device-001",
                timestamp=datetime(2026, 1, 15, 10, 30, 0),
                metric="temperature",
                value=23.5,
            ),
        ]

        inserted, duplicates = await EventService.insert_events_batch(mock_session, events)

        assert inserted == 2
        assert duplicates == 1

    @pytest.mark.asyncio
    async def test_insert_batch_all_duplicates(self):
        """Test batch where all events are duplicates."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        events = [
            EventCreate(
                device_id="device-001",
                timestamp=datetime(2026, 1, 15, 10, 30, 0),
                metric="temperature",
                value=23.5,
            ),
            EventCreate(
                device_id="device-001",
                timestamp=datetime(2026, 1, 15, 10, 31, 0),
                metric="temperature",
                value=23.7,
            ),
        ]

        inserted, duplicates = await EventService.insert_events_batch(mock_session, events)

        assert inserted == 0
        assert duplicates == 2