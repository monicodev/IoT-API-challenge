"""Unit tests for devices endpoints and service."""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock

from src.api.schemas.devices import DeviceInfo, DeviceListResponse
from src.services.device_service import DeviceService


class TestDeviceInfo:
    """Tests for DeviceInfo schema."""

    def test_device_info_creation(self):
        """Test device info with last event."""
        device = DeviceInfo(
            device_id="device-001",
            last_event_at=datetime(2026, 1, 15, 10, 30, 0),
        )
        assert device.device_id == "device-001"
        assert device.last_event_at == datetime(2026, 1, 15, 10, 30, 0)

    def test_device_info_no_last_event(self):
        """Test device info without last event."""
        device = DeviceInfo(device_id="device-001", last_event_at=None)
        assert device.device_id == "device-001"
        assert device.last_event_at is None


class TestDeviceListResponse:
    """Tests for DeviceListResponse schema."""

    def test_response_creation(self):
        """Test device list response."""
        response = DeviceListResponse(
            devices=[
                DeviceInfo(device_id="device-001", last_event_at=datetime(2026, 1, 15, 10, 30, 0)),
                DeviceInfo(device_id="device-002", last_event_at=datetime(2026, 1, 15, 10, 31, 0)),
            ],
            total=100,
            limit=50,
            offset=0,
        )
        assert len(response.devices) == 2
        assert response.total == 100


class TestDeviceService:
    """Tests for DeviceService using mocks."""

    @pytest.mark.asyncio
    async def test_list_devices_without_filter(self):
        """Test listing devices without since filter."""
        mock_session = AsyncMock()

        # Mock the query results
        mock_count_result = AsyncMock()
        mock_count_result.scalar.return_value = 10

        mock_query_result = AsyncMock()
        mock_query_result.fetchall.return_value = [
            ("device-001", datetime(2026, 1, 15, 10, 30, 0)),
            ("device-002", datetime(2026, 1, 15, 10, 31, 0)),
        ]

        # Setup session.execute to return different results for different queries
        async def execute_side_effect(*args, **kwargs):
            if hasattr(args[0], 'compare') and 'count' in str(args[0]):
                return mock_count_result
            return mock_query_result

        mock_session.execute.side_effect = execute_side_effect

        devices, total = await DeviceService.list_devices(
            session=mock_session,
            since=None,
            limit=50,
            offset=0,
        )

        assert total == 10
        assert len(devices) == 2
        assert devices[0].device_id == "device-001"

    @pytest.mark.asyncio
    async def test_list_devices_with_filter(self):
        """Test listing devices with since filter."""
        mock_session = AsyncMock()

        mock_count_result = AsyncMock()
        mock_count_result.scalar.return_value = 5

        mock_query_result = AsyncMock()
        mock_query_result.fetchall.return_value = [
            ("device-001", datetime(2026, 1, 15, 10, 30, 0)),
        ]

        async def execute_side_effect(*args, **kwargs):
            if hasattr(args[0], 'compare') and 'count' in str(args[0]):
                return mock_count_result
            return mock_query_result

        mock_session.execute.side_effect = execute_side_effect

        devices, total = await DeviceService.list_devices(
            session=mock_session,
            since=datetime(2026, 1, 1, 0, 0, 0),
            limit=50,
            offset=0,
        )

        assert total == 5

    @pytest.mark.asyncio
    async def test_list_devices_empty(self):
        """Test listing devices when none exist."""
        mock_session = AsyncMock()

        mock_count_result = AsyncMock()
        mock_count_result.scalar.return_value = 0

        mock_query_result = AsyncMock()
        mock_query_result.fetchall.return_value = []

        async def execute_side_effect(*args, **kwargs):
            if hasattr(args[0], 'compare') and 'count' in str(args[0]):
                return mock_count_result
            return mock_query_result

        mock_session.execute.side_effect = execute_side_effect

        devices, total = await DeviceService.list_devices(
            session=mock_session,
            since=None,
            limit=50,
            offset=0,
        )

        assert total == 0
        assert devices == []

    @pytest.mark.asyncio
    async def test_get_device_count(self):
        """Test getting device count."""
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar.return_value = 100
        mock_session.execute.return_value = mock_result

        count = await DeviceService.get_device_count(mock_session, since=None)

        assert count == 100

    @pytest.mark.asyncio
    async def test_get_device_count_with_filter(self):
        """Test getting device count with since filter."""
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar.return_value = 50
        mock_session.execute.return_value = mock_result

        count = await DeviceService.get_device_count(
            mock_session,
            since=datetime(2026, 1, 1, 0, 0, 0)
        )

        assert count == 50