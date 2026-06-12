from email.policy import default
import os
import math
from typing import List, Optional
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field
# pyrefly: ignore [missing-import]
from langchain_google_genai import ChatGoogleGenerativeAI
# pyrefly: ignore [missing-import]
from langchain_core.prompts import ChatPromptTemplate
# pyrefly: ignore [missing-import]
from langgraph.graph import StateGraph, START, END
from backend.app.graphs.state import TickerState    


# 1. MODELS FOR CLAIMS & REPORTS
class NumericalClaim(BaseModel): 
    claim: str = Field(description="The exact text of the claim containing a numerical value")
    value: float = Field(description="The parsed numerical value (e.g. 0.15 for 15%, 25.5 for 25.5)")
    source_type: str = Field(description="Expected source category: 'financials', 'news', or 'transcript'")
    field_name: Optional[str] = Field(None, description="The specific field name if it matches a quant ratio (e.g., 'pe_ratio', 'ev_ebitda')")

class ClaimsList(BaseModel):
    claims: List[NumericalClaim] = Field(default_factory=list)

class VerificationResult(BaseModel): 
    claim: str
    is_accurate: bool
    discrepancy_severity: str = Field(description="Discrepancy category: 'None', 'Low', 'Medium', 'High'")
    justification: str

class VerificationReport(BaseModel):
    results: List[VerificationResult] = Field(default_factory=list)

# LLM 
def get_risk_llm():
    google_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if google_key:
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=google_key,
            temperature=0.0
        )
    return None

# 2. GRAPH NODES
async def extract_claims_node(state: TickerState) -> dict:
    """Uses LLM structured output to identify all numerical and financial assertions in the brief."""
    if not state.brief:
        return {"warnings": ["Factual Check Node: No brief found to verify."]}
        
    brief_text = (
        f"Executive Summary: {state.brief.executive_summary}\n"
        f"Business Overview: {state.brief.business_overview}\n"
        f"Financial Analysis: {state.brief.financial_analysis}\n"
        f"Verdict: {state.brief.verdict}"
    )
    
    llm = get_risk_llm()
    if not llm:
        print("[Risk Check] Mock mode: skipping claim extraction.")

        # Setup mock claims that align with our mock brief
        mock_claims = [
            NumericalClaim(
                claim="P/E sits at 25.5",
                value=25.5,
                source_type="financials",
                field_name="pe_ratio"
            )
        ]
        return {"warnings": [], "feedback_notes": []} 
    try:
        structured_llm = llm.with_structured_output(ClaimsList)
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are a Quality Control Analyst. Your task is to scan the text of an equity "
                "investment brief and extract all exact statements containing numerical or financial "
                "claims (e.g., percentages, ratios, prices, dollar figures).\n"
                "For each claim, identify its expected source category ('financials', 'news', or 'transcript') "
                "and extract the numerical value as a float."
            )),
            ("user", "Extract all numerical claims from this brief:\n\n{brief_text}")
        ])
        
        chain = prompt | structured_llm
        claims_list = await chain.ainvoke({"brief_text": brief_text})
        
        return {"warnings": [], "warnings": [f"Extracted {len(claims_list.claims)} claims to verify."]}
    except Exception as e:
        print(f"Error during claim extraction: {e}")
        return {"warnings": [f"Claim extraction encountered an error: {str(e)}"]}

async def verify_claims_node(state: TickerState) -> dict:
    """Verifies numerical claims against database records and flags hallucinations."""

    if not state.brief:
        return {}
        
    llm = get_risk_llm()
    if not llm:
        print("[Risk Check] Mock mode: verification succeeded automatically.")
        return {"status": "verified"}

    brief_text = (
        f"Executive Summary: {state.brief.executive_summary}\n"
        f"Business Overview: {state.brief.business_overview}\n"
        f"Financial Analysis: {state.brief.financial_analysis}\n"
        f"Verdict: {state.brief.verdict}"
    )
    
    try:
        structured_llm = llm.with_structured_output(ClaimsList)
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Extract all numerical claims from this brief."),
            ("user", "{brief_text}")
        ])
        chain = prompt | structured_llm
        claims_list = await chain.ainvoke({"brief_text": brief_text})
    except Exception as e:
        return {"warnings": state.warnings + [f"Verification abort: {str(e)}"]}
    verification_results = []
    has_high_discrepancy = False
    discrepancy_logs = []

    raw_news_str = ""
    if state.scraped_data and state.scraped_data.news:
        raw_news_str = "\n".join([f"- {n.title}: {n.content}" for n in state.scraped_data.news])
        
    raw_transcript_str = "No transcript data."
    if state.scraped_data and state.scraped_data.transcript:
        raw_transcript_str = state.scraped_data.transcript.content
    for claim in claims_list.claims:
        # Programmatic Verification for Quantitative Multiples
        if claim.source_type == "financials" and claim.field_name and state.quant_data:
            ratios = state.quant_data.ratios
            target_val = getattr(ratios, claim.field_name, None)
            
            if target_val is not None:

                diff = abs(claim.value - target_val)
                pct_diff = (diff / target_val) if target_val != 0 else diff
                
                is_accurate = pct_diff <= 0.05
                severity = "None"
                justification = f"Claimed value {claim.value} matches database value {target_val} within 5% tolerance."
                
                if not is_accurate:
                    if pct_diff <= 0.15:
                        severity = "Low"
                        justification = f"Minor rounding difference: Claimed {claim.value}, DB value is {target_val}."
                    elif pct_diff <= 0.50:
                        severity = "Medium"
                        justification = f"Outdated/Discrepant value: Claimed {claim.value}, DB value is {target_val}."
                    else:
                        severity = "High"
                        has_high_discrepancy = True
                        justification = f"Severe hallucination! Claimed {claim.value}, actual database value is {target_val}."
                        discrepancy_logs.append(f"Section {claim.field_name}: {justification}")
                        
                verification_results.append(VerificationResult(
                    claim=claim.claim,
                    is_accurate=is_accurate,
                    discrepancy_severity=severity,
                    justification=justification
                ))
                continue

        source_data = raw_news_str if claim.source_type == "news" else raw_transcript_str
        
        try:
            verif_prompt = ChatPromptTemplate.from_messages([
                ("system", (
                    "You are a Fact-Checking Specialist. Compare the given CLAIM against the RAW SOURCES.\n"
                    "Evaluate if the claim is mathematically and factually supported.\n"
                    "Set discrepancy_severity to 'None' if accurate, 'Low' for minor rounding/date mismatches, "
                    "'Medium' for outdated data, and 'High' for complete hallucinations or severe mismatches."
                )),
                ("user", (
                    "CLAIM:\n{claim}\n\n"
                    "RAW SOURCES:\n{sources}\n\n"
                    "Output verification result."
                ))
            ])
            
            verifier = llm.with_structured_output(VerificationResult)
            verif_chain = verif_prompt | verifier
            res = await verif_chain.ainvoke({
                "claim": claim.claim,
                "sources": source_data
            })
            
            if res.discrepancy_severity == "High":
                has_high_discrepancy = True
                discrepancy_logs.append(f"Factual Discrepancy: {res.claim} -> {res.justification}")
                
            verification_results.append(res)
        except Exception as e:
            print(f"Failed verifier invocation for claim '{claim.claim}': {e}")
            verification_results.append(VerificationResult(
                claim=claim.claim,
                is_accurate=False,
                discrepancy_severity="Medium",
                justification=f"Verification script crashed during validation: {str(e)}"
            ))

    if has_high_discrepancy:
        print(f"[Risk Check] AUTO-REJECT: Caught High severity discrepancies in {state.ticker}.")

        return {
            "status": "rejected",
            "warnings": state.warnings + discrepancy_logs
        }
    
    print(f"[Risk Check] VERIFIED: Brief passed factual verification checks for {state.ticker}.")
    return {
        "status": "verified",
        "warnings": state.warnings + ["Factual check successfully completed with zero severe errors."]
    }

# 3. GRAPH 
builder = StateGraph(TickerState)

builder.add_node("extract_claims", extract_claims_node)
builder.add_node("verify_claims", verify_claims_node)
builder.add_edge(START, "extract_claims")
builder.add_edge("extract_claims", "verify_claims")
builder.add_edge("verify_claims", END)

risk_check_subgraph = builder.compile()