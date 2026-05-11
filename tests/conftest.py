"""Pytest configuration and shared fixtures."""

import asyncio
from collections.abc import Generator

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the entire test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def warm_up_api():
    """Wait for API to be ready before running tests."""
    from src.main import app

    transport = ASGITransport(app=app)
    max_retries = 10
    retry_delay = 0.5

    for attempt in range(max_retries):
        try:
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                response = await client.get("/health", timeout=5.0)
                if response.status_code == 200:
                    return
        except Exception:
            pass

        if attempt < max_retries - 1:
            await asyncio.sleep(retry_delay)

    pytest.fail(f"API did not become healthy after {max_retries} attempts")
