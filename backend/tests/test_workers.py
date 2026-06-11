# pyrefly: ignore [missing-import]
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.app.graphs.state import ScraperState, QuantState, FinancialMultiples
from backend.app.graphs.workers.quant import get_peers_for_ticker, calculate_ratios_node, fetch_market_data_node
from backend.app.graphs.workers.scraper import fetch_sec_filings_node, scrape_news_node

# ==========================================
# 1. Quant Tools & Calculations Tests
# ==========================================

def test_get_peers_for_ticker():
    # Tech giants test
    peers = get_peers_for_ticker("AAPL")
    assert "AAPL" not in peers
    assert len(peers) > 0
    
    # Fallback sector test
    default_peers = get_peers_for_ticker("UNKNOWN_TICKER")
    assert len(default_peers) == 3
    assert "AAPL" in default_peers


@pytest.mark.asyncio
async def test_calculate_ratios_node():
    # Mock financial info to feed to calculations
    mock_financials = {
        "info": {
            "trailingPE": 28.5,
            "enterpriseToEbitda": 18.2,
            "debtToEquity": 125.0,  # yfinance returns percent-scale for debt to equity
            "returnOnEquity": 0.22,
            "freeCashflow": 5000000,
            "marketCap": 100000000,
        }
    }
    state = QuantState(ticker="MSFT", financials=mock_financials)
    
    result = await calculate_ratios_node(state)
    ratios = result["calculated_ratios"]
    
    assert isinstance(ratios, FinancialMultiples)
    assert ratios.pe_ratio == 28.5
    assert ratios.ev_ebitda == 18.2
    assert ratios.debt_to_equity == 1.25  # Should convert 125.0% to decimal 1.25
    assert ratios.roe == 0.22
    assert ratios.free_cash_flow_yield == 0.05  # 5M / 100M = 0.05 (5%)


# ==========================================
# 2. Scraper Subgraph Mocked Tests
# ==========================================

@pytest.mark.asyncio
@patch("backend.app.graphs.workers.scraper.fetch_sec_filings")
async def test_fetch_sec_filings_node(mock_fetch):
    from backend.app.graphs.state import SecFiling
    
    # Set mock list of filings
    mock_fetch.return_value = [
        SecFiling(
            accession_number="0000320193-23-000106",
            form_type="10-K",
            filing_date="2023-10-31",
            report_url="https://sec.gov/10k",
            content_summary="Mock 10-K report details."
        )
    ]
    
    state = ScraperState(ticker="AAPL")
    result = await fetch_sec_filings_node(state)
    
    # Node calls fetch_sec_filings twice (once for 10-K, once for 10-Q), 
    # so we expect 2 combined items from the mock returns.
    assert "scraped_filings" in result
    assert len(result["scraped_filings"]) == 2
    assert result["scraped_filings"][0].accession_number == "0000320193-23-000106"


@pytest.mark.asyncio
@patch("backend.app.graphs.workers.scraper.scrape_news")
async def test_scrape_news_node(mock_scrape):
    from backend.app.graphs.state import NewsEntry
    
    mock_scrape.return_value = [
        NewsEntry(
            title="Apple Reports Strong Growth",
            url="https://news.example.com/aapl",
            content="Summary of Apple stock rising.",
            source="Financial News Provider"
        )
    ]
    
    state = ScraperState(ticker="AAPL", news_query="Apple financials")
    result = await scrape_news_node(state)
    
    assert "scraped_news" in result
    assert len(result["scraped_news"]) == 1
    assert result["scraped_news"][0].title == "Apple Reports Strong Growth"
