# pyrefly: ignore [missing-import]
import pytest
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
# pyrefly: ignore [missing-import]
from sqlalchemy import select
from backend.app.graphs.state import TickerState, InvestmentBrief, QuantOutput, FinancialMultiples
from backend.app.graphs.workers.synthesis import generate_brief_node
from backend.app.graphs.workers.risk_check import verify_claims_node, ClaimsList, NumericalClaim
from backend.app.services.evaluator import evaluate_brief
from backend.app.db.session import async_session
from backend.app.db.models import User, Thread, Brief, Evaluation

# ==========================================
# 1. Test Mock Synthesis & Error boundary
# ==========================================

@pytest.mark.asyncio
async def test_generate_brief_node_mock():
    # Verify that in mock mode, it correctly falls back to generating a structured Pydantic brief
    state = TickerState(ticker="AAPL")
    result = await generate_brief_node(state)
    
    assert "brief" in result
    assert isinstance(result["brief"], InvestmentBrief)
    assert result["brief"].ticker == "AAPL"


# ==========================================
# 2. Test Risk-Check Auto-Rejection Trigger
# ==========================================

@pytest.mark.asyncio
@patch("backend.app.graphs.workers.risk_check.get_risk_llm")
async def test_risk_check_auto_rejection(mock_get_llm):
    # Mock the LLM to return our specific claimed P/E ratio when invoked
    mock_llm = MagicMock()
    mock_chain = AsyncMock()
    
    # LangChain wraps structured_llm in a RunnableLambda which calls it directly as a function.
    # Therefore, we set the return value directly on the mock_chain callable itself.
    mock_chain.return_value = ClaimsList(claims=[
        NumericalClaim(
            claim="The calculated P/E ratio is 10.0",
            value=10.0,
            source_type="financials",
            field_name="pe_ratio"
        )
    ])
    mock_llm.with_structured_output.return_value = mock_chain
    mock_get_llm.return_value = mock_llm

    # 1. Setup quant data: P/E is 50.0
    quant_data = QuantOutput(
        ticker="AAPL",
        price_history_summary="Steady",
        ratios=FinancialMultiples(
            pe_ratio=50.0,  # DB has 50.0
            ev_ebitda=15.0,
            debt_to_equity=0.8,
            roe=0.25,
            free_cash_flow_yield=0.04
        )
    )
    
    # 2. Setup brief stating P/E is 10.0 (Huge discrepancy / hallucination)
    brief = InvestmentBrief(
        ticker="AAPL",
        executive_summary="Summary",
        business_overview="Overview",
        financial_analysis="The calculated P/E ratio is 10.0, which is very cheap.",
        risk_factors="None",
        verdict="BUY"
    )
    
    state = TickerState(
        ticker="AAPL",
        quant_data=quant_data,
        brief=brief,
        warnings=[]
    )
    
    # Run verification node
    result = await verify_claims_node(state)
    
    # We expect the brief to be rejected due to P/E discrepancy (claimed 10.0 vs actual 50.0)
    assert result["status"] == "rejected"
    assert any("Severe hallucination" in w for w in result["warnings"])


# ==========================================
# 3. Test Evaluator Database Integration
# ==========================================

@pytest.mark.asyncio
async def test_evaluator_database_persistence():
    # 1. Connect to active Postgres container (port 5435) via session pool
    async with async_session() as session:
        # Create a test user
        test_user = User(email=f"test_eval_{uuid.uuid4()}@example.com", password_hash="hash")
        session.add(test_user)
        await session.flush()  # Populates user ID
        
        # Create a test research thread
        test_thread = Thread(
            user_id=test_user.id,
            name="Test Audit Run",
            tickers=["AAPL"],
            status="running"
        )
        session.add(test_thread)
        await session.flush()
        
        # Create the brief
        test_brief = Brief(
            thread_id=test_thread.thread_id,
            ticker="AAPL",
            brief_content={
                "executive_summary": "Thesis details",
                "business_overview": "Overview",
                "financial_analysis": "P/E is standard",
                "risk_factors": "Risks are minor",
                "verdict": "BUY"
            }
        )
        session.add(test_brief)
        await session.flush()
        
        brief_id = test_brief.id
        brief_model = InvestmentBrief(
            ticker="AAPL",
            executive_summary="Thesis details",
            business_overview="Overview",
            financial_analysis="P/E is standard",
            risk_factors="Risks are minor",
            verdict="BUY"
        )
        
        # Run evaluation (calls evaluate_brief which writes to the database)
        rubric = await evaluate_brief(
            brief_id=brief_id,
            brief=brief_model,
            raw_news="News sources",
            raw_transcript="Transcript call details",
            raw_quant="Quant ratios details",
            db_session=session
        )
        
        # 2. Query DB to verify the Evaluation record is written to the 'eval_runs' table
        stmt = select(Evaluation).where(Evaluation.brief_id == brief_id)
        result = await session.execute(stmt)
        saved_eval = result.scalar_one_or_none()
        
        # Assertions
        assert saved_eval is not None
        assert saved_eval.score_factual == rubric.score_factual
        assert saved_eval.score_clarity == rubric.score_clarity
        assert saved_eval.score_coverage == rubric.score_coverage
        assert saved_eval.rubric_justification == rubric.rubric_justification
