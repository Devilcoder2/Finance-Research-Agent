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