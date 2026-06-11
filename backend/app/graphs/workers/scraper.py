from asyncio import sleep
import os 
import time
# pyrefly: ignore [missing-import]
import httpx
# pyrefly: ignore [missing-import]
from bs4 import BeautifulSoup
from typing import List, Optional
# pyrefly: ignore [missing-import]
from tavily import TavilyClient
# pyrefly: ignore [missing-import]
from langgraph.graph import StateGraph, START, END
from backend.app.graphs.state import ScraperState, NewsEntry, SecFiling, EarningsTranscript, ScraperOutput

SEC_HEADERS = {
    "User-Agent": os.getenv("SEC_USER_AGENT", "FinancialResearchAgent admin@financialresearchagent.local")
}


# 10 Reqs per second 
class TokenBucketLimiter: 
    def __init__(self, rate: int, capacity: int): 
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_check = time.time()

    def wait_for_token(self): 
        now = time.time()
        elapsed = now - self.last_check
        self.last_check = now
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        if self.tokens < 1: 
            sleep_time = (1 - self.tokens) / self.rate
            time.sleep(sleep_time)
            self.tokens = 0
        else: 
            self.tokens -= 1

sec_limiter = TokenBucketLimiter(rate=10, capacity=10)


# SEC EDGAR SCRAPER TOOL 
async def get_cik_for_ticker(ticker: str) -> Optional[str]: 
    """Fetches the SEC CIK code for a given ticker."""

    sec_limiter.wait_for_token()
    url = "https://www.sec.gov/files/company_tickers.json"

    async with httpx.AsyncClient() as client: 
        try: 
            response = await client.get(url, headers=SEC_HEADERS)
            if response.status_code == 200: 
                data = response.json()
                ticker_upper = ticker.upper()
                for key, val in data.items(): 
                    if val["ticker"] == ticker_upper: 
                        return str(val["cik_str"]).zfill(10)
        except Exception as e: 
            print(f"Error fetching CIK for ticker {ticker}: {e}")
    
    return None

async def fetch_sec_filings(ticker: str, form_type: str = "10-K") -> List[SecFiling]: 
    """Fetches recent SEC filings of form_type (10-K or 10-Q) for a ticker."""

    cik = await get_cik_for_ticker(ticker)
    if not cik: 
        print(f"No CIK found for ticker: {ticker}")
        return []
    
    sec_limiter.wait_for_token()
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    filings = []

    async with httpx.AsyncClient() as client: 
        try: 
            response = await client.get(url, headers=SEC_HEADERS)
            if response.status_code != 200:
                print(f"Failed to fetch filings metadata from SEC for CIK {cik}")
                return []
            
            data = response.json()
            recent_filings = data.get("filings", {}).get("recent", {})

            form_list = recent_filings.get("form", [])
            acc_num_list = recent_filings.get("accessionNumber", [])
            filing_date_list = recent_filings.get("filingDate", [])
            primary_doc_list = recent_filings.get("primaryDocument", [])

            count = 0
            for idx, form in enumerate(form_list):
                if form == form_type:
                    acc_num = acc_num_list[idx].replace("-", "")
                    primary_doc = primary_doc_list[idx]
                    filing_date = filing_date_list[idx]
                    
                    report_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_num}/{primary_doc}"
                    
                    # Store metadata; we retrieve a quick summary of the report
                    filings.append(SecFiling(
                        accession_number=acc_num_list[idx],
                        form_type=form_type,
                        filing_date=filing_date,
                        report_url=report_url,
                        content_summary=f"Recent {form_type} filing submitted on {filing_date}."
                    ))
                    
                    count += 1
                    if count >= 3:  # Only get the top 3 most recent filings
                        break
        
        except Exception as e: 
            print(f"Error fetching SEC filings for CIK {cik}: {e}")


# news & transcript tool (using tavily)

async def scrape_news(query: str, n_results: int = 5) -> List[NewsEntry]: 
    """Uses Tavily Search to locate and summarize recent financial news."""

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key: 
        print("Warning: TAVILY_API_KEY environment variable is not set. Returning mock news.")
        return [
            NewsEntry(
                title=f"Mock News for {query}",
                url="https://example.com/mock-news",
                content="Mock financial performance news snippet. Setup Tavily API key for real search.",
                source="Mock Financial Times"
            )
        ]
    
    try: 
        tavily = TavilyClient(api_key=api_key)
        response = tavily.search(query=query, max_results=n_results)
        
        results = response.get("results", [])
        news_entries = []
        for r in results:
            news_entries.append(NewsEntry(
                title=r.get("title", "No Title"),
                url=r.get("url", ""),
                content=r.get("snippet", ""),
                source=r.get("url", "").split("/")[2] if "/" in r.get("url", "") else "Web Search",
                published_date=None
            ))
        return news_entries

    except Exception as e: 
        print(f"Error querying Tavily search for news: {e}")
        return []

async def fetch_earnings_transcript(ticker: str) -> Optional[EarningsTranscript]: 
    """Uses Tavily search to fetch the latest public earnings call transcript text."""

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return EarningsTranscript(
            quarter="Q3",
            year=2023,
            content="Mock transcript details: Setup Tavily API key to extract actual call records."
        )
        
    query = f"{ticker} latest earnings call transcript text Motley Fool"
    try: 
        tavily = TavilyClient(api_key=api_key)
        response = tavily.search(query=query, max_results=1, include_raw_content=True)
        results = response.get("results", [])

        if results: 
            best_match = results[0]
            content = best_match.get("raw_content") or best_match.get("snippet", "")
            if len(content) > 5000:
                content = content[:5000] + "\n... [Truncated for brevity]"
                
            return EarningsTranscript(
                quarter="Latest",
                year=2024,
                content=content
            )
    except Exception as e: 
        print(f"Error fetching earnings transcript for {ticker}: {e}")
    
    return None
