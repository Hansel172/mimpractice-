import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from mcp.server.fastmcp import FastMCP
from investing_mcp import (
    get_portfolio_summary,
    get_stock_news,
    get_earnings,
    compare_stocks,
    get_watchlist_summary,
    get_sec_filings,
    research_company,
    get_insider_trades,
)

mcp = FastMCP("investing")


@mcp.tool()
def portfolio_summary(tickers: str) -> dict:
    """Get live prices and daily change for a list of stocks.
    Pass tickers as comma separated string e.g. 'AAPL, TSLA, NVDA'"""
    return get_portfolio_summary(tickers)


@mcp.tool()
def stock_news(ticker: str) -> dict:
    """Get the latest news headlines for a stock ticker."""
    return get_stock_news(ticker)


@mcp.tool()
def earnings(ticker: str) -> dict:
    """Get the last 4 quarters of revenue and net income for a company."""
    return get_earnings(ticker)


@mcp.tool()
def compare_two_stocks(ticker1: str, ticker2: str) -> dict:
    """Compare two stocks side by side — price, PE ratio, market cap, 52-week range."""
    return compare_stocks(ticker1, ticker2)


@mcp.tool()
def watchlist_summary(tickers: str) -> dict:
    """Check your full watchlist at once with signals.
    Pass tickers as comma separated string e.g. 'AAPL, TSLA, NVDA'"""
    return get_watchlist_summary(tickers)


@mcp.tool()
def sec_filings(ticker: str) -> dict:
    """Get the latest SEC filings (10-K, 10-Q, 8-K) for a company from EDGAR."""
    return get_sec_filings(ticker)


@mcp.tool()
def research_company_full(ticker: str) -> dict:
    """Full company breakdown — price, news, earnings, and SEC filings in one call."""
    return research_company(ticker)


@mcp.tool()
def insider_trades(ticker: str) -> dict:
    """Track insider buying and selling from SEC Form 4 filings.
    Insider buying with their own money is a strong bullish signal."""
    return get_insider_trades(ticker)


if __name__ == "__main__":
    mcp.run()
