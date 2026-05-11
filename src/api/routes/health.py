"""Health API route - handles deep healthcheck."""

import logging
import os

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from src.api.schemas.common import HealthResponse
from src.models.database import check_database_connection

router = APIRouter(prefix="/health", tags=["health"])
logger = logging.getLogger(__name__)


@router.get("", response_model=HealthResponse)
async def health_check() -> JSONResponse:
    """
    Deep healthcheck with real database connectivity check.

    Returns 200 if database is reachable, 503 if not.
    """
    db_url = os.environ.get("DATABASE_URL")
    is_connected, error = await check_database_connection(url=db_url)

    if is_connected:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=HealthResponse(
                status="healthy",
                database="connected",
            ).model_dump(),
        )
    else:
        logger.warning(f"[health] Database check failed: {error}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=HealthResponse(
                status="unhealthy",
                database="disconnected",
                error=error,
            ).model_dump(),
        )
