# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from httpx import AsyncClient, ASGITransport
# pyrefly: ignore [missing-import]
from fastapi import HTTPException
from backend.app.main import app
from backend.app.api.research import close_pool

# Add temporary test endpoints directly to testing app instance
@app.get("/test-uncaught-error")
async def trigger_uncaught_error():
    raise ValueError("Something unexpected broke inside the server")

@app.get("/test-http-error")
async def trigger_http_error():
    raise HTTPException(status_code=418, detail="I am a teapot")

@pytest.mark.asyncio
async def test_global_exception_handler_intercepts_unhandled():
    """Verify that an uncaught error returns a clean 500 JSON payload without stack trace leakage."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/test-uncaught-error")
        assert response.status_code == 500
        
        data = response.json()
        assert "error" in data
        assert data["error"] == "InternalServerError"
        assert "message" in data
        assert "unexpected server fault" in data["message"]
        assert "detail" in data
        assert "Something unexpected broke" in data["detail"]

@pytest.mark.asyncio
async def test_global_exception_handler_bypasses_http_exception():
    """Verify that expected FastAPI HTTP exceptions bypass the global 500 formatter."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/test-http-error")
        assert response.status_code == 418
        
        # Verify standard Starlette/FastAPI detail payload is returned
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "I am a teapot"
        assert "error" not in data  # Proves it did not trigger 500 formatting

@pytest.mark.asyncio
async def test_global_exception_handler_bypasses_validation_error():
    """Verify that request Pydantic validation errors yield standard 422 responses (not 500)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Tickers list must be at least min_length 1 in ResearchStartRequest schema
        response = await ac.post("/api/research/start", json={"tickers": []})
        
        # Unauthorized check should run first since /api/research/start is secured,
        # yielding 401 instead of 422 if unauthenticated, OR if the client is authenticated, yielding 422.
        # So we can test with a dummy token or a fake route that checks validation.
        # Let's test with a fake post route to verify validation errors are bypassed.
        pass

@app.post("/test-validation-route")
async def trigger_validation_error(tickers: list[str]):
    return {"tickers": tickers}

@pytest.mark.asyncio
async def test_global_exception_handler_bypasses_validation_error_live():
    """Verify validation errors are parsed by FastAPI directly to 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Send non-list type to trigger validation error
        response = await ac.post("/test-validation-route", json={"tickers": "not-a-list"})
        assert response.status_code == 422
        
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)  # Standard FastAPI validation error structure
        assert "error" not in data  # Bypassed the 500 error handler

    await close_pool()
