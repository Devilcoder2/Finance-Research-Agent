# pyrefly: ignore [missing-import]
import pytest
import uuid
import json
# pyrefly: ignore [missing-import]
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.api.research import close_pool

@pytest.mark.asyncio
async def test_research_api_lifecycle():
    # Setup AsyncClient with ASGITransport to hit our FastAPI app in-process
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        
        # Authenticate
        test_email = f"test_{uuid.uuid4()}@example.com"
        signup_res = await ac.post("/api/auth/signup", json={"email": test_email, "password": "password"})
        assert signup_res.status_code == 201
        login_res = await ac.post("/api/auth/login", json={"email": test_email, "password": "password"})
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        ac.headers["Authorization"] = f"Bearer {token}"
        
        # =====================================================================
        # 1. Start a new research thread
        # =====================================================================
        start_payload = {"tickers": ["AAPL", "MSFT"]}
        response = await ac.post("/api/research/start", json=start_payload)
        
        assert response.status_code == 201
        data = response.json()
        assert "thread_id" in data
        assert data["status"] == "initiated"
        
        thread_id = data["thread_id"]
        
        # =====================================================================
        # 2. Get listing of threads to verify registration
        # =====================================================================
        threads_response = await ac.get("/api/research/threads")
        assert threads_response.status_code == 200
        threads = threads_response.json()
        
        # Verify our thread is in the list
        matched_thread = next((t for t in threads if t["thread_id"] == thread_id), None)
        assert matched_thread is not None
        assert matched_thread["status"] == "initiated"
        assert set(matched_thread["tickers"]) == {"AAPL", "MSFT"}
        
        # =====================================================================
        # 3. Stream the research run and catch events
        # =====================================================================
        events_captured = []
        interrupts_payload = []
        
        async with ac.stream("GET", f"/api/research/stream/{thread_id}") as response_stream:
            assert response_stream.status_code == 200
            assert response_stream.headers["content-type"].startswith("text/event-stream")
            
            async for line in response_stream.aiter_lines():
                if line.startswith("data: "):
                    payload = json.loads(line[6:])
                    events_captured.append(payload)
                    if payload.get("event") == "interrupt":
                        interrupts_payload = payload.get("interrupts", [])
                        
        # Verify we received progress events
        assert len(events_captured) > 0
        assert any(e["event"] == "node_start" for e in events_captured)
        assert any(e["event"] == "interrupt" for e in events_captured)
        assert len(interrupts_payload) > 0
        
        # =====================================================================
        # 4. Check that status is now "paused"
        # =====================================================================
        threads_response = await ac.get("/api/research/threads")
        threads = threads_response.json()
        matched_thread = next((t for t in threads if t["thread_id"] == thread_id), None)
        assert matched_thread["status"] == "paused"
        
        # =====================================================================
        # 5. Resume execution by approving each ticker
        # =====================================================================
        # Loop through the pending interrupts and approve them
        for interrupt_item in interrupts_payload:
            ticker = interrupt_item["value"]
            resume_payload = {
                "thread_id": thread_id,
                "ticker": ticker,
                "action": "approve"
            }
            resume_response = await ac.post("/api/research/resume", json=resume_payload)
            assert resume_response.status_code == 200
            
        # =====================================================================
        # 6. Verify that the thread is completed and briefs are populated
        # =====================================================================
        threads_response = await ac.get("/api/research/threads")
        threads = threads_response.json()
        matched_thread = next((t for t in threads if t["thread_id"] == thread_id), None)
        assert matched_thread["status"] == "completed"
        
        briefs_response = await ac.get(f"/api/research/briefs/{thread_id}")
        assert briefs_response.status_code == 200
        briefs = briefs_response.json()
        
        assert len(briefs) == 2
        tickers_saved = {b["ticker"] for b in briefs}
        assert tickers_saved == {"AAPL", "MSFT"}
        assert "executive_summary" in briefs[0]["brief_content"]

    # Close pool connection at end of test to clean up
    await close_pool()
