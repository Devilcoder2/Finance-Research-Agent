import os
from typing import Optional
# pyrefly: ignore [missing-import]
from langchain_google_genai import ChatGoogleGenerativeAI
# pyrefly: ignore [missing-import]
from langchain_core.prompts import ChatPromptTemplate
# pyrefly: ignore [missing-import]
from langgraph.graph import StateGraph, START, END
from backend.app.graphs.state import TickerState, InvestmentBrief


def get_synthesis_llm():
    google_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    
    if google_key:
        print("[Synthesis] Using Google Gemini (gemini-1.5-pro)...")

        return ChatGoogleGenerativeAI(
            model="gemini-1.5-pro",
            google_api_key=google_key,
            temperature=0.2
        ).with_structured_output(InvestmentBrief)
    else:
        print("[Synthesis] No Google/Gemini API key found in environment. Running in mock/demo mode...")
        return None

# Mock Synthesis Generator (For testing/local runs without keys)
def generate_mock_brief(state: TickerState) -> InvestmentBrief:
    ticker = state.ticker.upper()
    
    # Grab metrics from quant data if available
    pe = "N/A"
    ev_ebitda = "N/A"
    if state.quant_data and state.quant_data.ratios:
        pe = f"{state.quant_data.ratios.pe_ratio:.2f}" if state.quant_data.ratios.pe_ratio else "N/A"
        ev_ebitda = f"{state.quant_data.ratios.ev_ebitda:.2f}" if state.quant_data.ratios.ev_ebitda else "N/A"
        
    return InvestmentBrief(
        ticker=ticker,
        executive_summary=(
            f"Mock Executive Summary for {ticker}. The company exhibits steady fundamentals. "
            f"Current multiples (P/E: {pe}, EV/EBITDA: {ev_ebitda}) indicate standard valuation."
        ),
        business_overview=(
            f"Mock Business Overview: {ticker} operates as a leader in its industry. "
            f"Revenues are driven by core services and subscription models."
        ),
        financial_analysis=(
            f"Mock Financial Analysis: Evaluated key historical trend values. P/E sits at {pe} "
            f"relative to sector peers. Balance sheet exhibits clean debt levels."
        ),
        risk_factors=(
            f"Mock Risk Factors: Downside risks include competitive pressure, macroeconomic inflation, "
            f"and regulatory compliance rules."
        ),
        verdict=f"VERDICT: HOLD. The company is fairly valued relative to peer group metrics."
    )

# Node Functions for the Subgraph
async def generate_brief_node(state: TickerState) -> dict:
    """Generates the structured investment brief using the Gemini LLM or mock fallback."""

    # 1. Compile context
    news_context = ""
    if state.scraped_data and state.scraped_data.news:
        news_context = "\n".join([f"- {n.title}: {n.content}" for n in state.scraped_data.news])
        
    filings_context = ""
    if state.scraped_data and state.scraped_data.filings:
        filings_context = "\n".join([f"- {f.form_type} ({f.filing_date}): {f.report_url}" for f in state.scraped_data.filings])
        
    transcript_context = "No recent transcripts."
    if state.scraped_data and state.scraped_data.transcript:
        transcript_context = state.scraped_data.transcript.content
        
    quant_context = "No quantitative metrics."
    if state.quant_data:
        r = state.quant_data.ratios
        peer_list = []
        if state.quant_data.peers_comparison:
            for p in state.quant_data.peers_comparison:
                pe_str = f"{p.pe_ratio}" if p.pe_ratio else "N/A"
                ev_str = f"{p.ev_ebitda}" if p.ev_ebitda else "N/A"
                peer_list.append(f"  - {p.ticker}: P/E {pe_str}, EV/EBITDA {ev_str}")
        peers_str = "\n".join(peer_list) if peer_list else "  No peer metrics available."
        quant_context = (
            f"Price History Summary: {state.quant_data.price_history_summary}\n"
            f"P/E Ratio: {r.pe_ratio or 'N/A'}\n"
            f"EV/EBITDA: {r.ev_ebitda or 'N/A'}\n"
            f"Debt/Equity: {r.debt_to_equity or 'N/A'}\n"
            f"ROE: {r.roe or 'N/A'}\n"
            f"Free Cash Flow Yield: {r.free_cash_flow_yield or 'N/A'}\n"
            f"Peer Multiples:\n{peers_str}"
        )
        
    feedback_context = "No feedback from previous runs."
    if state.feedback_notes:
        feedback_context = "\n".join([f"- Section '{f.section_id}': {f.comment}" for f in state.feedback_notes])

    # 2. Check LLM availability
    structured_llm = get_synthesis_llm()
    if not structured_llm:
        brief = generate_mock_brief(state)
        return {"brief": brief}
    
    # 3. Prompt setup
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are a Senior Equity Research Analyst. Your job is to compile a highly rigorous, "
            "factual, and detailed investment brief for the requested company ticker.\n"
            "You must split your output into the structured fields required: executive_summary, "
            "business_overview, financial_analysis, risk_factors, and verdict.\n"
            "Format the brief according to the final output Pydantic model structure. "
            "Incorporate all provided scraping context and quantitative financial multiples."
        )),
        ("user", (
            "Please generate an investment brief for {ticker}.\n\n"
            "--- Quantitative Data & Multiples ---\n"
            "{quant_context}\n\n"
            "--- Scraped News Summaries ---\n"
            "{news_context}\n\n"
            "--- SEC Filings metadata ---\n"
            "{filings_context}\n\n"
            "--- Latest Earnings Call Transcript Summary ---\n"
            "{transcript_context}\n\n"
            "--- Analyst Revision Feedback (If any) ---\n"
            "{feedback_context}\n\n"
            "Generate the brief now."
        ))
    ])
    # 4. Invoke LLM
    try:
        chain = prompt | structured_llm
        brief = await chain.ainvoke({
            "ticker": state["ticker"],
            "quant_context": quant_context,
            "news_context": news_context,
            "filings_context": filings_context,
            "transcript_context": transcript_context,
            "feedback_context": feedback_context
        })
        return {"brief": brief}
    except Exception as e:
        print(f"Error during LLM brief synthesis: {e}. Falling back to mock generator.")
        brief = generate_mock_brief(state)
        return {"brief": brief, "warnings": state.warnings + [f"Synthesis LLM failed, using mock data: {str(e)}"]}

    
#BUILD THE SUBGRAPH
builder = StateGraph(TickerState)

builder.add_node("generate_brief", generate_brief_node)
builder.add_edge(START, "generate_brief")
builder.add_edge("generate_brief", END)

synthesis_subgraph = builder.compile()
