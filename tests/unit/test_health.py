"""Unit tests for health endpoint."""
import pytest
from unittest.mock import AsyncMock, patch

from src.api.routes.health import health_check
from src.api.schemas.common import HealthResponse


class TestHealthCheck:
    """Tests for health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check_database_connected(self):
        """Test health check when database is connected."""
        with patch('src.api.routes.health.check_database_connection') as mock_check:
            mock_check.return_value = (True, "")
            
            response = await health_check()
            
            assert response.status_code == 200
            # JSONResponse status is in status_code attribute

    @pytest.mark.asyncio
    async def test_health_check_database_disconnected(self):
        """Test health check when database is disconnected.
        
        CRITICAL: This verifies the health endpoint properly returns 503
        when the database is not reachable.
        """
        with patch('src.api.routes.health.check_database_connection') as mock_check:
            mock_check.return_value = (False, "connection refused")
            
            response = await health_check()
            
            assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_health_check_database_timeout(self):
        """Test health check with database timeout."""
        with patch('src.api.routes.health.check_database_connection') as mock_check:
            mock_check.return_value = (False, "connection timeout")
            
            response = await health_check()
            
            assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_health_check_database_error(self):
        """Test health check with database error."""
        with patch('src.api.routes.health.check_database_connection') as mock_check:
            mock_check.return_value = (False, "invalid catalog name")
            
            response = await health_check()
            
            assert response.status_code == 503