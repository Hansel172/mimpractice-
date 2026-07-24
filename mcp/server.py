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
    get_robinhood_portfolio,
    get_robinhood_history,
    get_robinhood_buying_power,
    get_options_chain,
    get_open_option_positions,
    place_option_buy,
    close_option_position,
    place_option_with_stop_loss,
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


@mcp.tool()
def robinhood_portfolio() -> dict:
    """Get your real Robinhood portfolio — all positions, values, and gain/loss."""
    return get_robinhood_portfolio()


@mcp.tool()
def robinhood_history() -> dict:
    """Get your recent Robinhood trade history."""
    return get_robinhood_history()


@mcp.tool()
def robinhood_buying_power() -> dict:
    """Get your available cash and buying power in Robinhood."""
    return get_robinhood_buying_power()


@mcp.tool()
def options_chain(ticker: str, expiration_date: str = None) -> dict:
    """Get the options chain for a stock — all strikes, prices, IV, volume.
    If no expiration_date is given, returns the next available dates.
    expiration_date format: 'YYYY-MM-DD'"""
    return get_options_chain(ticker, expiration_date)


@mcp.tool()
def open_option_positions() -> dict:
    """Get your current open options positions from Robinhood."""
    return get_open_option_positions()


@mcp.tool()
def buy_option(ticker: str, strike: float, expiration: str, option_type: str,
               quantity: int, limit_price: float) -> dict:
    """Buy a call or put option on Robinhood with a limit price.
    option_type: 'call' or 'put'
    expiration: 'YYYY-MM-DD'
    limit_price: max price per share (1 contract = 100 shares)"""
    return place_option_buy(ticker, strike, expiration, option_type, quantity, limit_price)


@mcp.tool()
def sell_option(ticker: str, strike: float, expiration: str, option_type: str,
                quantity: int, limit_price: float) -> dict:
    """Sell (close) an options position on Robinhood.
    option_type: 'call' or 'put'
    expiration: 'YYYY-MM-DD'
    limit_price: minimum price per share you'll accept"""
    return close_option_position(ticker, strike, expiration, option_type, quantity, limit_price)


@mcp.tool()
def buy_option_with_stop_loss(ticker: str, strike: float, expiration: str, option_type: str,
                               quantity: int, buy_limit: float, stop_price: float) -> dict:
    """Buy an option AND set a stop loss in one command.
    Places the buy order then immediately sets a stop limit sell to protect downside.
    option_type: 'call' or 'put'
    expiration: 'YYYY-MM-DD'
    buy_limit: max price per share to pay
    stop_price: price per share that triggers the stop loss"""
    return place_option_with_stop_loss(ticker, strike, expiration, option_type,
                                       quantity, buy_limit, stop_price)


if __name__ == "__main__":
    mcp.run()
