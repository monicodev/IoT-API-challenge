"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import aggregate, devices, events, health
from src.models.database import engine

APP_NAME = "iot-telemetry-api"
try:
    APP_VERSION = version(APP_NAME)
except Exception:  # noqa: PERF203
    APP_VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown."""
    yield
    await engine.dispose()


app = FastAPI(
    title="IoT Telemetry API",
    description="High-performance API for IoT event ingestion and aggregation",
    version=APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(events.router)
app.include_router(aggregate.router)
app.include_router(devices.router)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint with API info."""
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "docs": "/docs",
    }
