# pyrefly: ignore [missing-import]
import pytest
import uuid
# pyrefly: ignore [missing-import]
from psycopg_pool import AsyncConnectionPool
# pyrefly: ignore [missing-import]
from psycopg.rows import dict_row
# pyrefly: ignore [missing-import]
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
# pyrefly: ignore [missing-import]
from langgraph.types import Command
# Import the builders so we can compile them with checkpointers dynamically in tests
from backend.app.graphs.supervisor import ticker_builder, portfolio_builder
from backend.app.graphs.state import TickerState, PortfolioState, InvestmentBrief

DB_CONNINFO = "postgresql://postgres:postgres@localhost:5435/financial_analyst"

# ==========================================
# 1. Test Parallel Execution & Fan-In
# ==========================================

@pytest.mark.asyncio
async def test_portfolio_parallel_execution():
    # Overwrite the human interrupt node to auto-approve in the builder
    async def mock_human_interrupt(state):
        print(f"[Test Mock] Auto-approving brief for {state.ticker} during portfolio test.")
        return {
            "status": "completed",
            "ticker_briefs": {state.ticker: state.brief}
        }
        
    original_review_node = ticker_builder.nodes["await_human_review"].runnable
    original_ticker_research = portfolio_builder.nodes["ticker_research"].runnable
    
    try:
        ticker_builder.nodes["await_human_review"].runnable = mock_human_interrupt
        
        # Re-compile ticker subgraph and register it on portfolio builder
        test_ticker_subgraph = ticker_builder.compile()
        portfolio_builder.nodes["ticker_research"].runnable = test_ticker_subgraph
        
        app = portfolio_builder.compile()
        
        state = PortfolioState(tickers=["AAPL", "MSFT"])
        res = await app.ainvoke(state)
        
        assert res["status"] == "completed"
        assert "portfolio_summary" in res
        assert isinstance(res["portfolio_summary"], str)
    finally:
        # Restore original runnables to avoid side-effects in other tests
        ticker_builder.nodes["await_human_review"].runnable = original_review_node
        portfolio_builder.nodes["ticker_research"].runnable = original_ticker_research


# ==========================================
# 2. Test State Checkpoint & Interrupt/Resume
# ==========================================

@pytest.mark.asyncio
async def test_ticker_interrupt_and_resume():
    # Set up the Postgres connection pool with min_size and psycopg row_factory dict_row
    async with AsyncConnectionPool(
        conninfo=DB_CONNINFO, 
        min_size=1, 
        max_size=2,
        kwargs={"autocommit": True, "row_factory": dict_row}
    ) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        # Ensure checkpoint tables are created in the test DB
        await checkpointer.setup()
        
        # Compile Ticker Graph with the active checkpointer
        app = ticker_builder.compile(checkpointer=checkpointer)
        
        # Create a unique thread configuration
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}
        
        state = TickerState(ticker="AAPL")
        
        # 1. Run the graph: It should run scraper, quant, synthesis, and halt at human review node
        res = await app.ainvoke(state, config=config)
        
        # Check that it paused at the interrupt
        state_info = await app.aget_state(config)
        assert len(state_info.next) > 0
        assert "await_human_review" in state_info.next
        
        # 2. Simulate resuming the thread with a mock decision payload (Approval)
        resume_payload = {"action": "approve"}
        
        # Resume execution using ainvoke with Command(resume=...)
        final_res = await app.ainvoke(Command(resume=resume_payload), config=config)
        
        # Verify the state indicates completed approval
        assert final_res["status"] == "completed"


# ==========================================
# 3. Test Revision Cap Limit (Loop Abort)
# ==========================================

@pytest.mark.asyncio
async def test_ticker_revision_cap_abort():
    async with AsyncConnectionPool(
        conninfo=DB_CONNINFO, 
        min_size=1, 
        max_size=2,
        kwargs={"autocommit": True, "row_factory": dict_row}
    ) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()
        
        app = ticker_builder.compile(checkpointer=checkpointer)
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}
        
        state = TickerState(ticker="AAPL")
        
        # First execution halts at human review
        await app.ainvoke(state, config=config)
        
        # Reject the brief 3 times. On the 4th reject, the graph should abort.
        for i in range(3):
            # Send rejection command
            resume_payload = {
                "action": "reject",
                "feedback": [{"section_id": "financial_analysis", "comment": f"Revision request {i+1}"}]
            }
            # Run graph by resuming with Command(resume=...)
            await app.ainvoke(Command(resume=resume_payload), config=config)
            
            state_info = await app.aget_state(config)
            if i < 2:
                # Still routing back to review
                assert "await_human_review" in state_info.next
            else:
                # 3rd reject (reaching revision_count = 3) will loop and then route to abort on the next check
                assert len(state_info.next) == 0  # Execution ended
                assert state_info.values["status"] == "failed"
                assert any("Aborted" in w for w in state_info.values["warnings"])
