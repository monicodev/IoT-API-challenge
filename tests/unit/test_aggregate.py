"""Unit tests for aggregate endpoints and service."""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch

from src.api.schemas.aggregate import (
    AggregationType,
    IntervalType,
    AggregateResponse,
    AggregateDataPoint,
)
from src.services.aggregation_service import AggregationService


class TestAggregationType:
    """Tests for AggregationType enum."""

    def test_all_aggregation_types(self):
        """Test all aggregation types are defined."""
        assert AggregationType.AVG.value == "avg"
        assert AggregationType.MIN.value == "min"
        assert AggregationType.MAX.value == "max"
        assert AggregationType.SUM.value == "sum"
        assert AggregationType.COUNT.value == "count"


class TestIntervalType:
    """Tests for IntervalType enum."""

    def test_all_interval_types(self):
        """Test all interval types are defined."""
        assert IntervalType.MINUTE.value == "1m"
        assert IntervalType.FIVE_MINUTES.value == "5m"
        assert IntervalType.HOUR.value == "1h"
        assert IntervalType.DAY.value == "1d"


class TestAggregationService:
    """Tests for AggregationService using mocks."""

    @pytest.mark.asyncio
    async def test_get_aggregation_hourly_avg(self):
        """Test hourly aggregation with avg."""
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.fetchall.return_value = [
            (datetime(2026, 1, 15, 10, 0, 0), 23.5),
            (datetime(2026, 1, 15, 11, 0, 0), 24.1),
        ]
        mock_session.execute.return_value = mock_result

        data = await AggregationService.get_aggregation(
            session=mock_session,
            device_id="device-001",
            metric="temperature",
            from_time=datetime(2026, 1, 15, 10, 0, 0),
            to=datetime(2026, 1, 15, 12, 0, 0),
            interval=IntervalType.HOUR,
            aggregation=AggregationType.AVG,
        )

        assert len(data) == 2
        assert data[0] == (datetime(2026, 1, 15, 10, 0, 0), 23.5)
        assert data[1] == (datetime(2026, 1, 15, 11, 0, 0), 24.1)

    @pytest.mark.asyncio
    async def test_get_aggregation_daily_max(self):
        """Test daily aggregation with max."""
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.fetchall.return_value = [
            (datetime(2026, 1, 15, 0, 0, 0), 30.5),
            (datetime(2026, 1, 16, 0, 0, 0), 28.3),
        ]
        mock_session.execute.return_value = mock_result

        data = await AggregationService.get_aggregation(
            session=mock_session,
            device_id="device-001",
            metric="temperature",
            from_time=datetime(2026, 1, 15, 0, 0, 0),
            to=datetime(2026, 1, 17, 0, 0, 0),
            interval=IntervalType.DAY,
            aggregation=AggregationType.MAX,
        )

        assert len(data) == 2
        assert data[0][1] == 30.5

    @pytest.mark.asyncio
    async def test_get_aggregation_count(self):
        """Test count aggregation."""
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.fetchall.return_value = [
            (datetime(2026, 1, 15, 10, 0, 0), 150.0),
            (datetime(2026, 1, 15, 11, 0, 0), 200.0),
        ]
        mock_session.execute.return_value = mock_result

        data = await AggregationService.get_aggregation(
            session=mock_session,
            device_id="device-001",
            metric="temperature",
            from_time=datetime(2026, 1, 15, 10, 0, 0),
            to=datetime(2026, 1, 15, 12, 0, 0),
            interval=IntervalType.HOUR,
            aggregation=AggregationType.COUNT,
        )

        assert len(data) == 2
        # COUNT returns float in our implementation

    @pytest.mark.asyncio
    async def test_get_aggregation_empty_result(self):
        """Test empty result when no data in range."""
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result

        data = await AggregationService.get_aggregation(
            session=mock_session,
            device_id="device-001",
            metric="temperature",
            from_time=datetime(2026, 1, 15, 10, 0, 0),
            to=datetime(2026, 1, 15, 12, 0, 0),
            interval=IntervalType.HOUR,
            aggregation=AggregationType.AVG,
        )

        assert data == []


class TestAggregateResponse:
    """Tests for aggregate response schema."""

    def test_response_creation(self):
        """Test aggregate response creation."""
        response = AggregateResponse(
            device_id="device-001",
            metric="temperature",
            interval="1h",
            aggregation="avg",
            data=[
                AggregateDataPoint(timestamp=datetime(2026, 1, 15, 10, 0, 0), value=23.5),
                AggregateDataPoint(timestamp=datetime(2026, 1, 15, 11, 0, 0), value=24.1),
            ],
        )

        assert response.device_id == "device-001"
        assert response.metric == "temperature"
        assert len(response.data) == 2