from email.policy import default
from typing import List, Dict, Any, Optional
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field


# 1. SCRAPER SUBGRAPH SCHEMAS 
class NewsEntry(BaseModel): 
    title: str = Field(description="Title of the news article")
    url: str = Field(description="URL of the news article")
    content: str = Field(description="Extracted text or summary of the article")
    source: str = Field(description="Publisher/Source name")
    published_date: Optional[str] = Field(None, description="Date of publication")

class SecFiling(BaseModel):
    accession_number: str = Field(description="Unique SEC accession number")
    form_type: str = Field(description="Form type e.g., '10-K' or '10-Q'")
    filing_date: str = Field(description="Filing date (YYYY-MM-DD)")
    report_url: str = Field(description="URL to the filing on SEC EDGAR")
    content_summary: str = Field(description="Extracted key parts or summary of the filing")

class EarningsTranscript(BaseModel): 
    quarter: str = Field(description="Financial quarter, e.g., 'Q1', 'Q2', 'Q3', 'Q4'")
    year: int = Field(description="Financial year")
    content: str = Field(description="Key summary or full text of the earnings call transcript")

class ScraperOutput(BaseModel): 
    """Unified container for all scraped financial research data."""
    ticker: str
    news: List[NewsEntry] = Field(default_factory=list)
    filings: List[SecFiling] = Field(default_factory=list)
    transcript: Optional[EarningsTranscript] = None

class ScraperState(BaseModel): 
    """Local state representing the state machine of the Scraper Subgraph."""
    ticker: str
    news_query: Optional[str] = None
    scraped_news: List[NewsEntry] = Field(default_factory=list)
    scraped_filings: List[SecFiling] = Field(default_factory=list)
    scraped_transcript: Optional[EarningsTranscript] = None
    error: Optional[str] = None



# 2. QUANT SUBGRAPH SCHEMAS 
class FinancialMultiples(BaseModel): 
    pe_ratio: Optional[float] = Field(None, description="Price to Earnings ratio")
    ev_ebitda: Optional[float] = Field(None, description="Enterprise Value to EBITDA")
    debt_to_equity: Optional[float] = Field(None, description="Total Debt to Total Equity ratio")
    roe: Optional[float] = Field(None, description="Return on Equity")
    free_cash_flow_yield: Optional[float] = Field(None, description="Free Cash Flow Yield")

class PeerMultiple(BaseModel): 
    ticker: str
    pe_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None

class QuantOutput(BaseModel): 
    """Unified container for quantitative financials and metrics."""
    ticker: str
    price_histroy_summary: str = Field(description="Brief text summary of historical prices")
    ratios: FinancialMultiples
    peers_comparison: List[PeerMultiple] = Field(default_factory=list)

class QuantState(BaseModel): 
    """Local state representing the state machine of the Quant Subgraph."""
    ticker: str
    price_history: Optional[Dict[str, Any]] = None
    financials: Optional[Dict[str, Any]] = None
    calculated_ratios: Optional[FinancialMultiples] = None
    peers: List[str] = Field(default_factory=list)
    peers_ratios: List[PeerMultiple] = Field(default_factory=list)
    error: Optional[str] = None
    