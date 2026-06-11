import os
# pyrefly: ignore [missing-import]
import yfinance as yf
from typing import List, Dict, Any, Optional
# pyrefly: ignore [missing-import]
from langgraph.graph import StateGraph, START, END
from backend.app.graphs.state import QuantState, FinancialMultiples, PeerMultiple, QuantOutput


def get_peers_for_ticker(ticker: str) -> List[str]:
    tech = {"AAPL", "MSFT", "GOOG", "GOOGL", "AMZN", "META", "NVDA", "NFLX"}
    finance = {"JPM", "BAC", "MS", "GS", "WFC", "C"}
    retail = {"WMT", "TGT", "COST", "HD", "LOW"}
    
    t = ticker.upper()
    if t in tech:
        return list(tech - {t})[:3]
    elif t in finance:
        return list(finance - {t})[:3]
    elif t in retail:
        return list(retail - {t})[:3]
    else:
        return ["AAPL", "MSFT", "GOOG"]


# Nodes for QUANT SUBGRAPH
async def fetch_market_data_node(state: QuantState) -> dict:
    """Fetches historical stock prices and financial statement data via yFinance."""

    ticker_str = state.ticker
    print(f"[Quant Node] Fetching yfinance data for {ticker_str}...")

    try: 
        ticker = yf.Ticker(ticker_str)

        hist = ticker.history(period="1y")
        price_history_summary = "No history available"
        if not hist.empty:
            start_price = hist["Close"].iloc[0]
            end_price = hist["Close"].iloc[-1]
            high_price = hist["High"].max()
            low_price = hist["Low"].min()
            pct_change = ((end_price - start_price) / start_price) * 100
            price_history_summary = (
                f"1-Year Price range: ${low_price:.2f} - ${high_price:.2f}. "
                f"Started at ${start_price:.2f}, ended at ${end_price:.2f} "
                f"({pct_change:+.2f}% change)."
            )
        
        info = ticker.info or {}
        def safe_to_dict(df):
            return df.to_dict() if df is not None and not df.empty else {}
        
        financials = {
            "info": info,
            "income_statement": safe_to_dict(ticker.income_stmt),
            "balance_sheet": safe_to_dict(ticker.balance_sheet),
            "cashflow": safe_to_dict(ticker.cashflow),
        }
        
        return {
            "price_history": {"summary": price_history_summary},
            "financials": financials,
            "peers": get_peers_for_ticker(ticker_str)
        }

    except Exception as e:
        return {"error": f"Failed fetching market data: {str(e)}"}

async def calculate_ratios_node(state: QuantState) -> dict:
    """Calculates PE, EV/EBITDA, Debt/Equity, ROE, and Free Cash Flow Yield."""
    
    print(f"[Quant Node] Calculating financial ratios for {state.ticker}...")
    
    if not state.financials:
        return {"error": "Missing financial statements to calculate ratios"}
        
    info = state.financials.get("info", {})
    
    try:
        pe_ratio = info.get("trailingPE") or info.get("forwardPE")
        
        ev_ebitda = info.get("enterpriseToEbitda")
        
        debt_to_equity = info.get("debtToEquity")
        if debt_to_equity is not None:
            if debt_to_equity > 2.0:
                debt_to_equity = debt_to_equity / 100.0
                
        roe = info.get("returnOnEquity")
        
        fcf_yield = info.get("freeCashflow")
        market_cap = info.get("marketCap")
        
        if fcf_yield and market_cap:
            fcf_yield = fcf_yield / market_cap
        else:
            fcf_yield = None
            
        ratios = FinancialMultiples(
            pe_ratio=pe_ratio,
            ev_ebitda=ev_ebitda,
            debt_to_equity=debt_to_equity,
            roe=roe,
            free_cash_flow_yield=fcf_yield
        )
        
        return {"calculated_ratios": ratios}
    except Exception as e:
        return {"error": f"Failed calculating ratios: {str(e)}"}

async def fetch_peer_data_node(state: QuantState) -> dict:
    """Fetches key multiples for peer competitors to assemble comparison metrics."""

    print(f"[Quant Node] Fetching peer comparisons for {state.peers}...")
    peers_ratios = []
    
    for peer_symbol in state.peers:
        try:
            peer_ticker = yf.Ticker(peer_symbol)
            info = peer_ticker.info or {}
            
            pe = info.get("trailingPE") or info.get("forwardPE")
            ev_eb = info.get("enterpriseToEbitda")
            
            peers_ratios.append(PeerMultiple(
                ticker=peer_symbol,
                pe_ratio=pe,
                ev_ebitda=ev_eb
            ))
        except Exception as e:
            print(f"Failed to fetch multiples for peer {peer_symbol}: {e}")
            peers_ratios.append(PeerMultiple(ticker=peer_symbol))
            
    return {"peers_ratios": peers_ratios}
