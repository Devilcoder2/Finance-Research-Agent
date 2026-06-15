# pyrefly: ignore [missing-import]
import pytest
import uuid
import json
# pyrefly: ignore [missing-import]
from sqlalchemy import select, text
# pyrefly: ignore [missing-import]
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.api.research import close_pool
from backend.app.db.session import async_session
from backend.app.db.models import CostMetric, User, Thread
from backend.app.services.cost_tracker import TokenTrackerCallback, save_cost_metric, calculate_gemini_cost

@pytest.mark.asyncio
async def test_hnsw_index_exists():
    """Verify that the HNSW index on long_term_memory table is active in the database."""
    async with async_session() as session:
        # Check pg_indexes system catalog for the specific index name
        stmt = text(
            "SELECT indexname FROM pg_indexes "
            "WHERE tablename = 'long_term_memory' AND indexname = 'long_term_memory_embedding_hnsw_idx';"
        )
        result = await session.execute(stmt)
        row = result.fetchone()
        
        assert row is not None
        assert row[0] == "long_term_memory_embedding_hnsw_idx"

@pytest.mark.asyncio
async def test_token_tracker_callback_parsing():
    """Verify that TokenTrackerCallback extracts tokens from LangChain responses correctly."""
    tracker = TokenTrackerCallback()
    
    # 1. Setup mock response with usage_metadata (modern standard)
    class MockMessage:
        def __init__(self, input_tokens, output_tokens):
            self.usage_metadata = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens
            }

    class MockGeneration:
        def __init__(self, message):
            self.message = message

    class MockLLMResult:
        def __init__(self, generations):
            self.generations = generations

    mock_msg = MockMessage(input_tokens=150, output_tokens=85)
    mock_gen = MockGeneration(message=mock_msg)
    mock_response = MockLLMResult(generations=[[mock_gen]])
    
    # Trigger callback
    await tracker.on_llm_end(
        response=mock_response,
        invocation_params={"model": "gemini-1.5-flash"}
    )
    
    assert "gemini-1.5-flash" in tracker.model_tokens
    assert tracker.model_tokens["gemini-1.5-flash"]["prompt"] == 150
    assert tracker.model_tokens["gemini-1.5-flash"]["completion"] == 85

@pytest.mark.asyncio
async def test_save_cost_metric_record():
    """Verify that save_cost_metric persists aggregated tokens and latencies to DB."""
    async with async_session() as session:
        # Create user & thread to satisfy foreign key constraints
        test_user = User(email=f"test_cost_{uuid.uuid4()}@example.com", password_hash="hash")
        session.add(test_user)
        await session.flush()
        
        test_thread = Thread(
            user_id=test_user.id,
            name="Test Cost Thread",
            tickers=["AAPL"],
            status="completed"
        )
        session.add(test_thread)
        await session.flush()
        
        thread_uuid = test_thread.thread_id
        tracker = TokenTrackerCallback()
        tracker.model_tokens = {
            "gemini-1.5-pro": {"prompt": 1000, "completion": 500},
            "gemini-1.5-flash": {"prompt": 2000, "completion": 1000}
        }
        
        # Save record
        db_record = await save_cost_metric(session, thread_uuid, tracker, latency=5.4)
        assert db_record is not None
        assert db_record.thread_id == thread_uuid
        assert db_record.prompt_tokens == 3000
        assert db_record.completion_tokens == 1500
        assert db_record.latency_seconds == 5.4
        
        # Verify pricing:
        # pro: (1000 * 1.25 + 500 * 5.00) / 1,000,000 = (1250 + 2500) / 1,000,000 = 0.00375
        # flash: (2000 * 0.075 + 1000 * 0.30) / 1,000,000 = (150 + 300) / 1,000,000 = 0.00045
        # total = 0.00420
        assert pytest.approx(db_record.estimated_cost_usd, rel=1e-5) == 0.00420

        # Query from DB to confirm persistence
        stmt = select(CostMetric).where(CostMetric.thread_id == thread_uuid)
        res = await session.execute(stmt)
        saved = res.scalar_one_or_none()
        assert saved is not None
        assert saved.prompt_tokens == 3000

@pytest.mark.asyncio
async def test_cost_metrics_logged_via_api():
    """Verify that a standard research API run logs cost metrics to DB on completion."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        
        # 1. Start run
        start_payload = {"tickers": ["AAPL"]}
        response = await ac.post("/api/research/start", json=start_payload)
        assert response.status_code == 201
        thread_id = response.json()["thread_id"]
        
        # 2. Stream
        events = []
        async with ac.stream("GET", f"/api/research/stream/{thread_id}") as stream:
            assert stream.status_code == 200
            async for line in stream.aiter_lines():
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))
                    
        # 3. Resume review interrupt
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
                
        # 4. Check DB for CostMetric
        async with async_session() as session:
            stmt = select(CostMetric).where(CostMetric.thread_id == uuid.UUID(thread_id))
            res = await session.execute(stmt)
            records = res.scalars().all()
            
            # Since mock runs might call multiple stages (e.g. stream and resume), we should assert 
            # we logged metrics for completed steps.
            assert len(records) >= 1
            for record in records:
                assert record.prompt_tokens > 0
                assert record.completion_tokens > 0
                assert record.estimated_cost_usd > 0
                assert record.latency_seconds > 0

    await close_pool()
