"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.models.database import engine
from src.api.routes import events, aggregate, devices, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup: nothing needed - migrations run via docker-compose
    yield
    # Shutdown: dispose engine connections
    await engine.dispose()


app = FastAPI(
    title="IoT Telemetry API",
    description="High-performance API for IoT event ingestion and aggregation",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router)
app.include_router(events.router)
app.include_router(aggregate.router)
app.include_router(devices.router)


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "IoT Telemetry API",
        "version": "1.0.0",
        "docs": "/docs",
    }