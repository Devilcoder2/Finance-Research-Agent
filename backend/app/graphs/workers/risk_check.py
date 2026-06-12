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