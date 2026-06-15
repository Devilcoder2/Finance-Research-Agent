# pyrefly: ignore [missing-import]
import pytest
import logging
# pyrefly: ignore [missing-import]
from httpx import AsyncClient, ASGITransport
# pyrefly: ignore [missing-import]
from fastapi import Depends
from backend.app.main import app
from backend.app.db.session import get_db
from backend.app.api.research import close_pool

# Add a temporary test endpoint to trigger a database session rollback log
@app.get("/test-db-error")
async def trigger_db_error(db = Depends(get_db)):
    # Simulating a transaction error that triggers rollback
    raise ValueError("Simulated database transaction error")

@pytest.mark.asyncio
async def test_logger_configurations():
    """Verify that backend loggers are registered correctly."""
    api_logger = logging.getLogger("backend.api")
    db_logger = logging.getLogger("backend.db.session")
    
    assert api_logger is not None
    assert db_logger is not None

@pytest.mark.asyncio
async def test_request_logging_middleware(caplog):
    """Verify that HTTP requests write duration and status code details to the log."""
    caplog.set_level(logging.INFO)
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
        assert response.status_code == 200
        
        # Verify that our middleware logged the request
        request_logs = [r.message for r in caplog.records if "backend.api" in r.name]
        assert len(request_logs) >= 1
        
        # Check logged content format
        log_msg = request_logs[0]
        assert "Method: GET" in log_msg
        assert "Path: /" in log_msg
        assert "Status: 200" in log_msg
        assert "Duration:" in log_msg

@pytest.mark.asyncio
async def test_database_rollback_logging(caplog):
    """Verify that database transaction exceptions trigger rollback logging with traceback info."""
    caplog.set_level(logging.ERROR)
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # We expect a 500 error since ValueError is raised
        with pytest.raises(ValueError, match="Simulated database transaction error"):
            await ac.get("/test-db-error")
            
        # Verify that our database session logger captured the rollback trace details
        db_logs = [r for r in caplog.records if r.name == "backend.db.session"]
        assert len(db_logs) >= 1
        assert "Database transaction error. Rolling back session:" in db_logs[0].message
        assert db_logs[0].levelname == "ERROR"
        assert db_logs[0].exc_info is not None  # Verifies traceback is present

    await close_pool()
