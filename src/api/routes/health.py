"""Health API route - handles deep healthcheck."""
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from src.models.database import check_database_connection
from src.api.schemas.common import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def health_check() -> JSONResponse:
    """
    Deep healthcheck with real database connectivity check.

    Returns 200 if database is reachable, 503 if not.
    """
    is_connected, error = await check_database_connection()

    if is_connected:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=HealthResponse(
                status="healthy",
                database="connected",
            ).model_dump(),
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=HealthResponse(
                status="unhealthy",
                database="disconnected",
                error=error,
            ).model_dump(),
        )