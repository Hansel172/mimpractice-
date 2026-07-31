import os
import yfinance as yf
import httpx
from dotenv import load_dotenv
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

load_dotenv()

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
TO_EMAIL         = os.getenv("TO_EMAIL")
FROM_EMAIL       = os.getenv("FROM_EMAIL")
NEWS_API_KEY     = "ec86790d8a8349bba91acd058157a73d"

WATCHLIST = ["MSFT", "GOOGL", "META", "PLTR", "NVDA", "AMD", "AAPL"]
INDEXES   = ["SPY", "QQQ", "IBIT"]


def get_news(ticker):
    try:
        stock = yf.Ticker(ticker.upper())
        company_name = stock.info.get("longName", ticker)
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": f"{ticker.upper()} stock OR {company_name} stock",
            "sortBy": "publishedAt",
            "pageSize": 5,
            "language": "en",
            "apiKey": NEWS_API_KEY
        }
        resp = httpx.get(url, params=params, timeout=10)
        articles = resp.json().get("articles", [])
        return company_name, [
            {"title": a["title"], "source": a["source"]["name"], "published": a["publishedAt"][:10]}
            for a in articles[:3]
        ]
    except Exception:
        return ticker, []


def build_email():
    today = datetime.now().strftime("%A, %B %d, %Y")
    sections = []

    # ── WATCHLIST ALERTS ──────────────────────────────────────────────────────
    print("Checking watchlist...")
    watchlist_rows = ""
    for ticker in WATCHLIST:
        try:
            stock     = yf.Ticker(ticker)
            fast      = stock.fast_info
            price     = round(fast.last_price, 2)
            year_high = round(fast.year_high, 2)
            pct       = round(((price - year_high) / year_high) * 100, 1)

            in_zone = -35 <= pct <= -18
            status  = "🟢 In Zone" if in_zone else "⚪ Watch"
            color   = "#2ecc71" if in_zone else "#888"

            watchlist_rows += f"""
            <tr>
              <td style="padding:8px 12px;font-weight:bold;">{ticker}</td>
              <td style="padding:8px 12px;">${price}</td>
              <td style="padding:8px 12px;">${year_high}</td>
              <td style="padding:8px 12px;">{pct}%</td>
              <td style="padding:8px 12px;color:{color};">{status}</td>
            </tr>"""
        except Exception:
            continue

    sections.append(f"""
    <div style="margin-bottom:32px;">
      <h2 style="color:#cc0000;border-bottom:1px solid #333;padding-bottom:8px;">Watchlist Alerts</h2>
      <p style="color:#aaa;font-size:0.9em;margin-bottom:12px;">🟢 In Zone = stock pulled back 18–35% from 52w high (options entry range)</p>
      <table style="width:100%;border-collapse:collapse;background:#1a1a1a;border-radius:8px;">
        <tr style="background:#2a0000;color:#aaa;font-size:0.85em;">
          <th style="padding:8px 12px;text-align:left;">Ticker</th>
          <th style="padding:8px 12px;text-align:left;">Price</th>
          <th style="padding:8px 12px;text-align:left;">52w High</th>
          <th style="padding:8px 12px;text-align:left;">From High</th>
          <th style="padding:8px 12px;text-align:left;">Status</th>
        </tr>
        {watchlist_rows}
      </table>
    </div>""")

    # ── MARKET OVERVIEW ───────────────────────────────────────────────────────
    print("Fetching market overview...")
    market_rows = ""
    labels = {"SPY": "S&P 500", "QQQ": "Nasdaq", "IBIT": "Bitcoin ETF"}
    for ticker in INDEXES:
        try:
            fast    = yf.Ticker(ticker).fast_info
            price   = round(fast.last_price, 2)
            prev    = round(fast.previous_close, 2)
            chg     = round(price - prev, 2)
            chg_pct = round((chg / prev) * 100, 2)
            arrow   = "▲" if chg >= 0 else "▼"
            color   = "#2ecc71" if chg >= 0 else "#e74c3c"
            market_rows += f"""
            <tr>
              <td style="padding:8px 12px;font-weight:bold;">{labels.get(ticker, ticker)}</td>
              <td style="padding:8px 12px;">${price}</td>
              <td style="padding:8px 12px;color:{color};">{arrow} {chg_pct}%</td>
            </tr>"""
        except Exception:
            continue

    sections.append(f"""
    <div style="margin-bottom:32px;">
      <h2 style="color:#cc0000;border-bottom:1px solid #333;padding-bottom:8px;">Market Overview</h2>
      <table style="width:100%;border-collapse:collapse;background:#1a1a1a;border-radius:8px;">
        <tr style="background:#2a0000;color:#aaa;font-size:0.85em;">
          <th style="padding:8px 12px;text-align:left;">Index</th>
          <th style="padding:8px 12px;text-align:left;">Price</th>
          <th style="padding:8px 12px;text-align:left;">Today</th>
        </tr>
        {market_rows}
      </table>
    </div>""")

    # ── NEWS ON WATCHLIST ─────────────────────────────────────────────────────
    print("Fetching news...")
    news_html = ""
    for ticker in WATCHLIST:
        company_name, headlines = get_news(ticker)
        if not headlines:
            continue
        items = "".join([
            f'<li style="margin-bottom:6px;color:#ccc;">'
            f'<span style="color:#aaa;font-size:0.85em;">{hl["source"]} · {hl["published"]}</span><br>'
            f'{hl["title"]}</li>'
            for hl in headlines
        ])
        news_html += f"""
        <div style="margin-bottom:20px;">
          <h3 style="color:#ff6666;margin-bottom:8px;">{ticker} — {company_name}</h3>
          <ul style="padding-left:18px;margin:0;">{items}</ul>
        </div>"""

    sections.append(f"""
    <div style="margin-bottom:32px;">
      <h2 style="color:#cc0000;border-bottom:1px solid #333;padding-bottom:8px;">Watchlist News</h2>
      {news_html}
    </div>""")

    # ── ASSEMBLE ──────────────────────────────────────────────────────────────
    body = "\n".join(sections)
    return f"""
    <div style="background:#0f0f0f;color:#f0f0f0;font-family:Georgia,serif;max-width:700px;margin:0 auto;padding:40px 20px;">
      <div style="text-align:center;margin-bottom:40px;border-bottom:2px solid #cc0000;padding-bottom:24px;">
        <h1 style="color:#cc0000;letter-spacing:3px;margin:0;">MORNING BRIEFING</h1>
        <p style="color:#aaa;margin-top:8px;font-style:italic;">{today}</p>
      </div>
      {body}
      <div style="text-align:center;color:#444;font-size:0.8em;margin-top:40px;border-top:1px solid #222;padding-top:20px;">
        Automated · Data from Yahoo Finance + NewsAPI
      </div>
    </div>"""


def send_briefing():
    print(f"Building morning briefing for {TO_EMAIL}...")
    html = build_email()

    today   = datetime.now().strftime("%B %d, %Y")
    message = Mail(
        from_email   = FROM_EMAIL,
        to_emails    = TO_EMAIL,
        subject      = f"Morning Briefing — {today}",
        html_content = html
    )

    try:
        sg       = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        if response.status_code in (200, 202):
            print(f"✓ Briefing sent to {TO_EMAIL}")
        else:
            print(f"SendGrid response: {response.status_code}")
    except Exception as e:
        print(f"Error sending email: {e}")


if __name__ == "__main__":
    send_briefing()
