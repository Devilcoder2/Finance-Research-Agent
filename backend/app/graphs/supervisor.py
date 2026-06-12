import os
from typing import List, Dict, Any
# pyrefly: ignore [missing-import]
from langgraph.graph import StateGraph, START, END
# pyrefly: ignore [missing-import]
from langgraph.types import Send, interrupt
# pyrefly: ignore [missing-import]
from langchain_google_genai import ChatGoogleGenerativeAI
# pyrefly: ignore [missing-import]
from langchain_core.prompts import ChatPromptTemplate
# Import subgraphs and state definitions
from backend.app.graphs.state import TickerState, PortfolioState, ScraperState, QuantState, ScraperOutput, QuantOutput, InvestmentBrief
from backend.app.graphs.workers.scraper import scraper_subgraph
from backend.app.graphs.workers.quant import quant_subgraph
from backend.app.graphs.workers.synthesis import synthesis_subgraph
from backend.app.graphs.workers.risk_check import risk_check_subgraph

# NODE FUNCTIONS
async def run_scraper_node(state: TickerState) -> dict:
    """Runs the nested Scraper Subgraph for the target ticker."""
    print(f"[Ticker Graph] Invoking Scraper Subgraph for {state.ticker}...")
    scraper_input = ScraperState(ticker=state.ticker)
    res = await scraper_subgraph.ainvoke(scraper_input)
    
    if res.get("error"):
        return {"warnings": state.warnings + [f"Scraper error: {res['error']}"]}
        
    scraper_output = ScraperOutput(
        ticker=state.ticker,
        news=res.get("scraped_news", []),
        filings=res.get("scraped_filings", []),
        transcript=res.get("scraped_transcript")
    )
    return {"scraped_data": scraper_output}


async def run_quant_node(state: TickerState) -> dict:
    """Runs the nested Quant Subgraph for the target ticker."""
    print(f"[Ticker Graph] Invoking Quant Subgraph for {state.ticker}...")
    quant_input = QuantState(ticker=state.ticker)
    res = await quant_subgraph.ainvoke(quant_input)
    
    if res.get("error"):
        return {"warnings": state.warnings + [f"Quant error: {res['error']}"]}
        
    quant_output = QuantOutput(
        ticker=state.ticker,
        price_history_summary=res.get("price_history", {}).get("summary", "No history summary."),
        ratios=res.get("calculated_ratios"),
        peers_comparison=res.get("peers_ratios", [])
    )
    return {"quant_data": quant_output}

async def route_post_synthesis(state: TickerState):
    """Routes to Risk-Check after brief synthesis."""
    return "run_risk_check"

async def route_post_risk_check(state: TickerState):
    """
    Evaluates risk check outputs: Rejects and routes back to synthesis if discrepancy
    is caught, otherwise proceeds to human review.
    """
    status = state.status
    if status == "rejected":
        if state.revision_count >= 3:
            print(f"[Ticker Graph] Max revisions exceeded for {state.ticker}. Aborting.")
            return "abort_max_revisions"
        print(f"[Ticker Graph] Discrepancies found. Routing {state.ticker} back to synthesis (Rev: {state.revision_count + 1}).")
        return "loop_back_synthesis"
    
    return "await_human_review"

async def loop_back_synthesis_node(state: TickerState) -> dict:
    """Increments the revision counter when the Risk-Check rejects the brief."""
    return {"revision_count": state.revision_count + 1}

async def human_interrupt_node(state: TickerState) -> dict:
    """
    Halts execution before final publication to capture human approvals or annotation comments.
    """

    print(f"[Ticker Graph] Interrupt breakpoint. Awaiting analyst review for {state.ticker}...")
    review_payload = {
        "ticker": state.ticker,
        "brief": state.brief.model_dump() if state.brief else None,
        "warnings": state.warnings
    }
    
    decision = interrupt(review_payload)
    
    action = decision.get("action")  # 'approve' or 'reject'
    feedback = decision.get("feedback", [])  # list of SectionAnnotation
    
    if action == "approve":
        print(f"[Ticker Graph] Analyst APPROVED research brief for {state.ticker}.")
        return {"status": "completed"}
    else:
        print(f"[Ticker Graph] Analyst REJECTED research brief for {state.ticker}. Feedback logged.")
        return {
            "status": "revision",
            "feedback_notes": feedback,
            "revision_count": state.revision_count + 1
        }

async def route_post_human_review(state: TickerState):
    """Routes to completion, or loops back to synthesis if the analyst rejected the brief."""

    if state.status == "completed":
        return END
    if state.revision_count > 3:
        return "abort_max_revisions"
        
    return "run_synthesis"

async def abort_max_revisions_node(state: TickerState) -> dict:
    """Node representing failure state when revision threshold is breached."""

    return {"status": "failed", "warnings": state.warnings + ["Aborted: Maximum revision limit of 3 exceeded."]}


# PORTFOLIO GRAPH NODE FUNCTIONS & ROUTER
async def load_memories_node(state: PortfolioState) -> dict:
    """Queries vector storage (pgvector) to load long-term user research preferences."""

    print(f"[Portfolio Graph] Initializing session. Retrieving memories for {state.tickers}...")
    # Mock lookup; we will wire the actual pgvector later
    mock_memories = [
        "Analyst preference: Prefers conservative EV/EBITDA multiples in high-growth tech profiles."
    ]
    return {"memories": mock_memories}

def fan_out_tickers_routing(state: PortfolioState):
    """Sends parallel jobs to research each ticker concurrently."""
    print(f"[Portfolio Graph] Fanning out parallel research for: {state.tickers}")
    return [Send("ticker_research", TickerState(ticker=t)) for t in state.tickers]