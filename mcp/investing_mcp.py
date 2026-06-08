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


def get_watchlist_summary(tickers: str) -> dict:
    """Check your entire watchlist at once — prices, change, and a signal."""
    ticker_list = [t.strip().upper() for t in tickers.split(",")]
    watchlist = []

    for ticker in ticker_list:
        stock = yf.Ticker(ticker)
        fast = stock.fast_info
        info = stock.info

        try:
            price = round(fast.last_price, 2)
            prev_close = round(fast.previous_close, 2)
            change_pct = round(((price - prev_close) / prev_close) * 100, 2)
            year_high = round(fast.year_high, 2)
            year_low = round(fast.year_low, 2)
            pct_from_high = round(((price - year_high) / year_high) * 100, 2)

            if change_pct > 2:
                signal = "STRONG MOVE UP"
            elif change_pct < -2:
                signal = "STRONG MOVE DOWN"
            elif pct_from_high > -5:
                signal = "NEAR 52W HIGH"
            else:
                signal = "NEUTRAL"

            watchlist.append({
                "ticker": ticker,
                "company": info.get("shortName", ticker),
                "price": f"${price}",
                "change_today": f"{change_pct}%",
                "pct_from_52w_high": f"{pct_from_high}%",
                "signal": signal
            })
        except Exception:
            watchlist.append({"ticker": ticker, "error": "Could not fetch"})

    return {"watchlist": watchlist}


def get_sec_filings(ticker: str) -> dict:
    """Get the latest SEC filings for a company from EDGAR."""
    stock = yf.Ticker(ticker.upper())
    company_name = stock.info.get("longName", ticker)
    headers = {"User-Agent": "InvestingMCP research@example.com"}

    try:
        # Step 1: get CIK from EDGAR ticker lookup
        tickers_resp = httpx.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers=headers, timeout=10
        )
        tickers_data = tickers_resp.json()
        cik = None
        for entry in tickers_data.values():
            if entry["ticker"].upper() == ticker.upper():
                cik = str(entry["cik_str"]).zfill(10)
                break

        if not cik:
            return {"ticker": ticker.upper(), "error": "CIK not found"}

        # Step 2: get filings for that CIK
        filings_resp = httpx.get(
            f"https://data.sec.gov/submissions/CIK{cik}.json",
            headers=headers, timeout=10
        )
        data = filings_resp.json()
        recent = data.get("filings", {}).get("recent", {})

        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        descriptions = recent.get("primaryDocument", [])

        filings = []
        for form, date, desc in zip(forms, dates, descriptions):
            if form in ["10-K", "10-Q", "8-K"]:
                filings.append({"form": form, "filed": date, "document": desc})
            if len(filings) == 5:
                break

        return {
            "ticker": ticker.upper(),
            "company": company_name,
            "recent_filings": filings
        }
    except Exception as e:
        return {"ticker": ticker.upper(), "error": str(e)}


def research_company(ticker: str) -> dict:
    """Full company breakdown — price, news, earnings, and SEC filings in one call."""
    stock = yf.Ticker(ticker.upper())
    info = stock.info
    fast = stock.fast_info

    try:
        price = round(fast.last_price, 2)
        prev_close = round(fast.previous_close, 2)
        change_pct = round(((price - prev_close) / prev_close) * 100, 2)
        market_cap = fast.market_cap
        pe_ratio = info.get("trailingPE", "N/A")
        year_high = round(fast.year_high, 2)
        year_low = round(fast.year_low, 2)

        overview = {
            "ticker": ticker.upper(),
            "company": info.get("longName", ticker),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "description": info.get("longBusinessSummary", "N/A")[:300] + "...",
            "price": f"${price}",
            "change_today": f"{change_pct}%",
            "market_cap": f"${round(market_cap / 1_000_000_000, 2)}B" if market_cap else "N/A",
            "pe_ratio": round(pe_ratio, 2) if isinstance(pe_ratio, float) else "N/A",
            "52w_high": f"${year_high}",
            "52w_low": f"${year_low}",
            "dividend_yield": info.get("dividendYield", "None")
        }
    except Exception as e:
        overview = {"ticker": ticker.upper(), "error": str(e)}

    news = get_stock_news(ticker)
    earnings = get_earnings(ticker)
    filings = get_sec_filings(ticker)

    return {
        "overview": overview,
        "latest_news": news.get("headlines", [])[:3],
        "earnings": earnings.get("last_4_quarters", [])[:2],
        "sec_filings": filings.get("recent_filings", [])[:3]
    }


def get_insider_trades(ticker: str) -> dict:
    """Track insider buying and selling — Form 4 filings from SEC EDGAR.
    When executives buy their own stock with their own money, that's a bullish signal.
    When they sell large amounts, that can be a warning sign.
    """
    headers = {"User-Agent": "InvestingMCP research@example.com"}
    stock = yf.Ticker(ticker.upper())
    company_name = stock.info.get("longName", ticker)

    try:
        # Step 1: get CIK
        tickers_resp = httpx.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers=headers, timeout=10
        )
        tickers_data = tickers_resp.json()
        cik = None
        for entry in tickers_data.values():
            if entry["ticker"].upper() == ticker.upper():
                cik = str(entry["cik_str"]).zfill(10)
                break

        if not cik:
            return {"ticker": ticker.upper(), "error": "CIK not found"}

        # Step 2: get Form 4 filings (insider trades)
        filings_resp = httpx.get(
            f"https://data.sec.gov/submissions/CIK{cik}.json",
            headers=headers, timeout=10
        )
        data = filings_resp.json()
        recent = data.get("filings", {}).get("recent", {})

        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        reporters = recent.get("primaryDocument", [])

        # Step 3: find all Form 4 entries
        insider_filings = []
        for form, date, doc in zip(forms, dates, reporters):
            if form == "4":
                insider_filings.append({"filed": date, "document": doc})
            if len(insider_filings) == 10:
                break

        if not insider_filings:
            return {
                "ticker": ticker.upper(),
                "company": company_name,
                "message": "No recent insider trades found"
            }

        # Step 4: parse each Form 4 for transaction details
        trades = []
        for filing in insider_filings[:5]:
            try:
                doc_parts = filing["document"].replace(".htm", "").replace(".xml", "")
                xml_url = (
                    f"https://www.sec.gov/cgi-bin/browse-edgar"
                    f"?action=getcompany&CIK={cik}&type=4&dateb=&owner=include&count=10&output=atom"
                )
                trades.append({
                    "filed": filing["filed"],
                    "form": "Form 4 (Insider Trade)",
                    "sec_link": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=4&dateb=&owner=include&count=10"
                })
            except Exception:
                continue

        # Step 5: also get summary from yfinance insider data
        insider_summary = []
        try:
            insider_df = stock.insider_transactions
            if insider_df is not None and not insider_df.empty:
                for _, row in insider_df.head(8).iterrows():
                    shares = row.get("Shares", 0)
                    action = "BOUGHT" if shares > 0 else "SOLD"
                    insider_summary.append({
                        "insider": row.get("Insider", "Unknown"),
                        "position": row.get("Position", "N/A"),
                        "action": action,
                        "shares": f"{abs(int(shares)):,}",
                        "value": f"${abs(int(row.get('Value', 0))):,}",
                        "date": str(row.get("Start Date", "N/A"))[:10]
                    })
        except Exception:
            pass

        return {
            "ticker": ticker.upper(),
            "company": company_name,
            "insider_trades": insider_summary if insider_summary else trades,
            "view_all_filings": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=4&dateb=&owner=include&count=40"
        }

    except Exception as e:
        return {"ticker": ticker.upper(), "error": str(e)}


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
