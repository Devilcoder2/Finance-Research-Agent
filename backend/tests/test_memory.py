# pyrefly: ignore [missing-import]
import pytest
import uuid
# pyrefly: ignore [missing-import]
from sqlalchemy import select
from backend.app.db.session import async_session
from backend.app.db.models import User, Thread, Brief, LongTermMemory
from backend.app.services.vector_store import embed_text, save_memory, search_memories
from backend.app.graphs.state import PortfolioState, TickerState, InvestmentBrief
from backend.app.graphs.supervisor import load_memories_node, fan_out_tickers_routing
from backend.app.graphs.workers.synthesis import generate_brief_node

@pytest.mark.asyncio
async def test_embedding_generation():
    text = "Some random preference text for stock analysis"
    vec = await embed_text(text)
    
    assert isinstance(vec, list)
    assert len(vec) == 768
    assert all(isinstance(val, float) for val in vec)

@pytest.mark.asyncio
async def test_save_and_search_memories():
    async with async_session() as session:
        user_uuid = uuid.UUID("00000000-0000-0000-0000-000000000000")
        
        # Ensure we have our default user in db if not exists
        user_check = await session.execute(select(User).where(User.id == user_uuid))
        db_user = user_check.scalar_one_or_none()
        if not db_user:
            db_user = User(id=user_uuid, email="analyst@example.com", password_hash="hash")
            session.add(db_user)
            await session.commit()
            
        # Clean up any existing memories for test tickers to keep it isolated
        await session.execute(
            LongTermMemory.__table__.delete().where(
                LongTermMemory.ticker.in_(["XYZ", "ABC"])
            )
        )
        await session.commit()

        # Save some memories
        m1 = await save_memory(session, user_uuid, "XYZ", "financial_analysis", "Prefers high gross margins")
        m2 = await save_memory(session, user_uuid, "XYZ", "risk_factors", "Dislikes high debt levels")
        m3 = await save_memory(session, user_uuid, "ABC", "verdict", "Prefers high growth dividends")

        # Query XYZ memories
        xyz_memories = await search_memories(session, user_uuid, ["XYZ"], limit=5)
        assert len(xyz_memories) == 2
        assert any("margins" in m for m in xyz_memories)
        assert any("debt" in m for m in xyz_memories)
        assert not any("dividends" in m for m in xyz_memories)

        # Query ABC memories
        abc_memories = await search_memories(session, user_uuid, ["ABC"], limit=5)
        assert len(abc_memories) == 1
        assert "dividends" in abc_memories[0]

        # Multi-ticker search
        all_memories = await search_memories(session, user_uuid, ["XYZ", "ABC"], limit=5)
        assert len(all_memories) == 3

@pytest.mark.asyncio
async def test_load_memories_node_and_routing():
    async with async_session() as session:
        user_uuid = uuid.UUID("00000000-0000-0000-0000-000000000000")
        
        # Insert a memory specifically for TSLA
        await session.execute(
            LongTermMemory.__table__.delete().where(LongTermMemory.ticker == "TSLA")
        )
        await session.commit()
        
        await save_memory(session, user_uuid, "TSLA", "executive_summary", "Watch regulatory credits closely")

        # Execute load_memories_node
        state = PortfolioState(tickers=["TSLA", "MSFT"])
        result = await load_memories_node(state)
        
        assert "memories" in result
        assert len(result["memories"]) >= 1
        assert any("credits" in m for m in result["memories"])

        # Execute fan_out_tickers_routing and check that only TSLA gets its memory
        full_state = PortfolioState(tickers=["TSLA", "MSFT"], memories=result["memories"])
        sends = fan_out_tickers_routing(full_state)
        
        tsla_job = next(s for s in sends if s.arg.ticker == "TSLA")
        msft_job = next(s for s in sends if s.arg.ticker == "MSFT")
        
        assert len(tsla_job.arg.memories) == 1
        assert "credits" in tsla_job.arg.memories[0]
        assert len(msft_job.arg.memories) == 0

@pytest.mark.asyncio
async def test_synthesis_prompt_injection():
    # Verify generate_brief_node compiles and processes memories context correctly
    state = TickerState(
        ticker="TSLA",
        memories=["Analyst preference for TSLA: Watch regulatory credits closely"]
    )
    result = await generate_brief_node(state)
    
    assert "brief" in result
    assert isinstance(result["brief"], InvestmentBrief)
    # The actual LLM calls are mocked/fallback in standard test suite run, but we verify the structured brief returned.
