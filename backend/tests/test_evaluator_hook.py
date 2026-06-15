# pyrefly: ignore [missing-import]
import pytest
import uuid
import json
from sqlalchemy import select
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.api.research import close_pool
from backend.app.db.session import async_session
from backend.app.db.models import Evaluation

@pytest.mark.asyncio
async def test_evaluator_hook_during_api_run():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        
        # Authenticate
        test_email = f"test_{uuid.uuid4()}@example.com"
        await ac.post("/api/auth/signup", json={"email": test_email, "password": "password"})
        login_res = await ac.post("/api/auth/login", json={"email": test_email, "password": "password"})
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        ac.headers["Authorization"] = f"Bearer {token}"
        
        # 1. Start research for a ticker
        start_payload = {"tickers": ["AAPL"]}
        response = await ac.post("/api/research/start", json=start_payload)
        assert response.status_code == 201
        thread_id = response.json()["thread_id"]
        
        # 2. Stream the run to completion/interrupt
        events = []
        async with ac.stream("GET", f"/api/research/stream/{thread_id}") as stream:
            assert stream.status_code == 200
            async for line in stream.aiter_lines():
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))
                    
        # 3. Resume review (Approval)
        interrupt_events = [e for e in events if e.get("event") == "interrupt"]
        if interrupt_events:
            for item in interrupt_events[0]["interrupts"]:
                resume_payload = {
                    "thread_id": thread_id,
                    "ticker": item["value"],
                    "action": "approve"
                }
                resume_res = await ac.post("/api/research/resume", json=resume_payload)
                assert resume_res.status_code == 200
                
        # 4. Fetch briefs and check that evaluations are populated
        briefs_res = await ac.get(f"/api/research/briefs/{thread_id}")
        assert briefs_res.status_code == 200
        briefs = briefs_res.json()
        
        assert len(briefs) == 1
        assert "evaluations" in briefs[0]
        assert len(briefs[0]["evaluations"]) >= 1
        
        eval_item = briefs[0]["evaluations"][0]
        assert "score_factual" in eval_item
        assert "score_clarity" in eval_item
        assert "score_coverage" in eval_item
        assert "rubric_justification" in eval_item
        
        # Confirm they exist in DB
        async with async_session() as session:
            db_evals = await session.execute(
                select(Evaluation).where(Evaluation.brief_id == uuid.UUID(briefs[0]["id"]))
            )
            saved = db_evals.scalars().all()
            assert len(saved) >= 1

    await close_pool()
