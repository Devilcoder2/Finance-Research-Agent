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

async def generate_portfolio_summary_node(state: PortfolioState) -> dict:
    """
    Fans back in. Combines fanned-out ticker briefs and executes an LLM call 
    to summarize and compare the stock profiles.
    """
    print(f"[Portfolio Graph] Fan-in. Synthesizing comparative summary for {state.tickers}...")
    
    briefs_list = []
    for ticker, brief in state.ticker_briefs.items():
        briefs_list.append(
            f"--- {ticker} Investment Brief ---\n"
            f"Executive Summary: {brief.executive_summary}\n"
            f"Verdict: {brief.verdict}\n"
        )
    briefs_context = "\n".join(briefs_list)
    
    google_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not google_key:
        print("[Portfolio Graph] Mock summary compiled (no API key).")
        summary = f"Mock Portfolio Summary comparing: {', '.join(state.tickers)}. Setup Gemini API key for comparative analysis."
        return {"portfolio_summary": summary, "status": "completed"}
        
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=google_key, temperature=0.3)
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are a Senior Investment Portfolio Manager. Read the fanned-out individual stock briefs "
                "and write a highly professional, comparative summary table and analysis contrasting their "
                "thesis potentials, valuations, and risk exposures."
            )),
            ("user", "Compare these briefs and compile the portfolio overview:\n\n{briefs_context}")
        ])
        
        chain = prompt | llm
        res = await chain.ainvoke({"briefs_context": briefs_context})
        return {"portfolio_summary": res.content, "status": "completed"}
    except Exception as e:
        print(f"Error compiling portfolio summary: {e}")
        return {"portfolio_summary": f"Error during summary: {str(e)}", "status": "failed"}

def merge_ticker_briefs(state: PortfolioState):
    """Aggregate all ticker briefs from ticker_research runs."""
    return "generate_summary"

# COMPILING THE SUBGRAPH
ticker_builder = StateGraph(TickerState)

ticker_builder.add_node("run_scraper", run_scraper_node)
ticker_builder.add_node("run_quant", run_quant_node)
ticker_builder.add_node("run_synthesis", synthesis_subgraph)
ticker_builder.add_node("run_risk_check", risk_check_subgraph)
ticker_builder.add_node("loop_back_synthesis", loop_back_synthesis_node)
ticker_builder.add_node("await_human_review", human_interrupt_node)
ticker_builder.add_node("abort_max_revisions", abort_max_revisions_node)

ticker_builder.add_edge(START, "run_scraper")
ticker_builder.add_edge(START, "run_quant")

ticker_builder.add_conditional_edges("run_synthesis", route_post_synthesis, {
    "run_risk_check": "run_risk_check"
})
ticker_builder.add_conditional_edges("run_risk_check", route_post_risk_check, {
    "loop_back_synthesis": "loop_back_synthesis",
    "abort_max_revisions": "abort_max_revisions",
    "await_human_review": "await_human_review"
})
ticker_builder.add_conditional_edges("await_human_review", route_post_human_review, {
    END: END,
    "abort_max_revisions": "abort_max_revisions",
    "run_synthesis": "run_synthesis"
})

ticker_builder.add_edge("loop_back_synthesis", "run_synthesis")

ticker_builder.add_edge("abort_max_revisions", END)
ticker_subgraph = ticker_builder.compile()

# COMPILE PORTFOLIO GRAPH
portfolio_builder = StateGraph(PortfolioState)

portfolio_builder.add_node("load_memories", load_memories_node)
portfolio_builder.add_node("ticker_research", ticker_subgraph)
portfolio_builder.add_node("generate_summary", generate_portfolio_summary_node)

portfolio_builder.add_edge(START, "load_memories")
portfolio_builder.add_conditional_edges("load_memories", fan_out_tickers_routing, ["ticker_research"])
portfolio_builder.add_edge("ticker_research", "generate_summary")
portfolio_builder.add_edge("generate_summary", END)

portfolio_graph = portfolio_builder.compile()