# pyrefly: ignore [missing-import]
import pytest
import asyncio
from backend.app.db.session import engine

@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for all async tests to share."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
def cleanup_db_connections():
    """Dispose SQLAlchemy engine at the end of each test (handles both sync and async test contexts)."""
    yield
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            # Schedule task inside the active event loop
            loop.create_task(engine.dispose())
    except RuntimeError:
        # No loop running, run until complete in a temporary loop
        temp_loop = asyncio.new_event_loop()
        temp_loop.run_until_complete(engine.dispose())
        temp_loop.close()
