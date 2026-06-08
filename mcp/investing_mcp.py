import yfinance as yf
import httpx
import json

NEWS_API_KEY = "ec86790d8a8349bba91acd058157a73d"


def get_portfolio_summary(tickers: str) -> dict:
    """Get current prices and daily change for a list of tickers.
    Pass tickers as a comma separated string like 'AAPL, TSLA, NVDA'
    """
    ticker_list = [t.strip().upper() for t in tickers.split(",")]
    results = []

    for ticker in ticker_list:
        stock = yf.Ticker(ticker)
        info = stock.fast_info

        try:
            price = round(info.last_price, 2)
            prev_close = round(info.previous_close, 2)
            change = round(price - prev_close, 2)
            change_pct = round((change / prev_close) * 100, 2)

            results.append({
                "ticker": ticker,
                "price": f"${price}",
                "change": f"${change}",
                "change_percent": f"{change_pct}%",
                "trend": "UP" if change >= 0 else "DOWN"
            })
        except Exception:
            results.append({"ticker": ticker, "error": "Could not fetch data"})

    return {"portfolio": results}


def get_stock_news(ticker: str) -> dict:
    """Get the latest news headlines for a stock ticker."""
    stock = yf.Ticker(ticker.upper())
    company_name = stock.info.get("longName", ticker)

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": f"{ticker.upper()} stock OR {company_name} stock OR {ticker.upper()} shares",
        "sortBy": "publishedAt",
        "pageSize": 5,
        "language": "en",
        "apiKey": NEWS_API_KEY
    }

    response = httpx.get(url, params=params)
    data = response.json()

    articles = data.get("articles", [])
    headlines = [
        {
            "title": a["title"],
            "source": a["source"]["name"],
            "published": a["publishedAt"][:10]
        }
        for a in articles
    ]

    return {
        "ticker": ticker.upper(),
        "company": company_name,
        "headlines": headlines
    }


def get_earnings(ticker: str) -> dict:
    """Get the last 4 quarters of earnings for a company."""
    stock = yf.Ticker(ticker.upper())
    company_name = stock.info.get("longName", ticker)

    income = stock.quarterly_income_stmt
    if income is None or income.empty:
        return {"ticker": ticker.upper(), "error": "No earnings data found"}

    results = []
    for date in income.columns[:4]:
        net_income = income.loc["Net Income", date] if "Net Income" in income.index else None
        revenue = income.loc["Total Revenue", date] if "Total Revenue" in income.index else None
        results.append({
            "quarter": str(date)[:10],
            "net_income": f"${round(float(net_income) / 1_000_000_000, 2)}B" if net_income else "N/A",
            "revenue": f"${round(float(revenue) / 1_000_000_000, 2)}B" if revenue else "N/A"
        })

    return {
        "ticker": ticker.upper(),
        "company": company_name,
        "last_4_quarters": results
    }


def compare_stocks(ticker1: str, ticker2: str) -> dict:
    """Compare two stocks side by side — price, change, PE ratio, market cap."""
    results = {}

    for ticker in [ticker1.upper(), ticker2.upper()]:
        stock = yf.Ticker(ticker)
        info = stock.info
        fast = stock.fast_info

        try:
            price = round(fast.last_price, 2)
            prev_close = round(fast.previous_close, 2)
            change_pct = round(((price - prev_close) / prev_close) * 100, 2)
            market_cap = fast.market_cap
            pe_ratio = info.get("trailingPE", "N/A")

            results[ticker] = {
                "price": f"${price}",
                "change_today": f"{change_pct}%",
                "market_cap": f"${round(market_cap / 1_000_000_000, 2)}B" if market_cap else "N/A",
                "pe_ratio": round(pe_ratio, 2) if isinstance(pe_ratio, float) else "N/A",
                "52w_high": f"${round(fast.year_high, 2)}",
                "52w_low": f"${round(fast.year_low, 2)}"
            }
        except Exception as e:
            results[ticker] = {"error": str(e)}

    return {"comparison": results}


if __name__ == "__main__":
    print("=== PORTFOLIO SUMMARY ===")
    portfolio = get_portfolio_summary("AAPL, TSLA, NVDA")
    print(json.dumps(portfolio, indent=2))

    print("\n=== STOCK NEWS ===")
    news = get_stock_news("AAPL")
    print(json.dumps(news, indent=2))

    print("\n=== EARNINGS ===")
    earnings = get_earnings("AAPL")
    print(json.dumps(earnings, indent=2))

    print("\n=== COMPARE STOCKS ===")
    comparison = compare_stocks("AAPL", "MSFT")
    print(json.dumps(comparison, indent=2))
