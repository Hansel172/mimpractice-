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
        "q": company_name,
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


if __name__ == "__main__":
    print("=== PORTFOLIO SUMMARY ===")
    portfolio = get_portfolio_summary("AAPL, TSLA, NVDA")
    print(json.dumps(portfolio, indent=2))

    print("\n=== STOCK NEWS ===")
    news = get_stock_news("AAPL")
    print(json.dumps(news, indent=2))
