import os
import yfinance as yf
import httpx
import random
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
INDEXES   = {"SPY": "S&P 500", "QQQ": "Nasdaq 100", "IBIT": "Bitcoin ETF"}
MACRO     = {"GC=F": "Gold", "CL=F": "Crude Oil", "DX-Y.NYB": "US Dollar (DXY)", "BTC-USD": "Bitcoin"}
SECTORS   = {
    "XLK":  "Technology",
    "XLC":  "Communication",
    "XLY":  "Consumer Disc.",
    "XLF":  "Financials",
    "XLI":  "Industrials",
    "XLV":  "Health Care",
    "XLP":  "Consumer Staples",
    "XLB":  "Materials",
    "XLRE": "Real Estate",
    "XLU":  "Utilities",
    "XLE":  "Energy",
}

QUOTES = [
    ("The stock market is a device for transferring money from the impatient to the patient.", "Warren Buffett"),
    ("In investing, what is comfortable is rarely profitable.", "Robert Arnott"),
    ("The four most dangerous words in investing are: 'This time it's different.'", "Sir John Templeton"),
    ("Risk comes from not knowing what you're doing.", "Warren Buffett"),
    ("The market is filled with individuals who know the price of everything, but the value of nothing.", "Philip Fisher"),
    ("Be fearful when others are greedy, and greedy when others are fearful.", "Warren Buffett"),
    ("An investment in knowledge pays the best interest.", "Benjamin Franklin"),
    ("The individual investor should act consistently as an investor and not as a speculator.", "Ben Graham"),
    ("Wide diversification is only required when investors do not understand what they are doing.", "Warren Buffett"),
    ("Opportunities come infrequently. When it rains gold, put out the bucket, not the thimble.", "Warren Buffett"),
    ("The best investment you can make is in yourself.", "Warren Buffett"),
    ("I will tell you how to become rich. Close the doors. Be fearful when others are greedy. Be greedy when others are fearful.", "Warren Buffett"),
    ("It's not whether you're right or wrong, but how much money you make when you're right and how much you lose when you're wrong.", "George Soros"),
    ("The most contrarian thing of all is not to oppose the crowd but to think for yourself.", "Peter Thiel"),
    ("Bulls make money, bears make money, pigs get slaughtered.", "Wall Street Proverb"),
]


def fetch(ticker):
    try:
        fast = yf.Ticker(ticker).fast_info
        price = round(fast.last_price, 2)
        prev  = round(fast.previous_close, 2)
        chg   = round(price - prev, 2)
        pct   = round((chg / prev) * 100, 2)
        return price, chg, pct
    except Exception:
        return None, None, None


def arrow_color(pct):
    if pct is None:
        return "—", "#666"
    arrow = "▲" if pct >= 0 else "▼"
    color = "#2ecc71" if pct >= 0 else "#e74c3c"
    return arrow, color


def get_news(ticker):
    try:
        stock = yf.Ticker(ticker.upper())
        company_name = stock.info.get("longName", ticker)
        params = {
            "q": f"{ticker.upper()} stock OR {company_name} stock",
            "sortBy": "publishedAt",
            "pageSize": 5,
            "language": "en",
            "apiKey": NEWS_API_KEY
        }
        resp = httpx.get("https://newsapi.org/v2/everything", params=params, timeout=10)
        articles = resp.json().get("articles", [])
        return company_name, [
            {"title": a["title"], "source": a["source"]["name"], "published": a["publishedAt"][:10]}
            for a in articles[:3]
        ]
    except Exception:
        return ticker, []


def section_header(title):
    return f'<h2 style="color:#cc0000;border-bottom:1px solid #2a2a2a;padding-bottom:10px;margin-bottom:20px;letter-spacing:1px;font-size:1.1em;text-transform:uppercase;">{title}</h2>'


def build_email():
    today = datetime.now().strftime("%A, %B %d, %Y")
    sections = []

    # ── 1. MARKET PULSE ───────────────────────────────────────────────────────
    print("Fetching market pulse...")
    pulse_cells = ""
    for ticker, label in INDEXES.items():
        price, chg, pct = fetch(ticker)
        ar, col = arrow_color(pct)
        price_str = f"${price:,.2f}" if price else "N/A"
        pct_str   = f"{ar} {abs(pct):.2f}%" if pct is not None else "—"
        pulse_cells += f"""
        <td style="padding:16px 20px;text-align:center;border-right:1px solid #222;">
          <div style="color:#aaa;font-size:0.8em;margin-bottom:4px;">{label}</div>
          <div style="font-size:1.3em;font-weight:bold;color:#fff;">{price_str}</div>
          <div style="color:{col};font-size:0.9em;margin-top:4px;">{pct_str}</div>
        </td>"""

    # VIX
    vix_price, _, _ = fetch("^VIX")
    vix_str = f"{vix_price:.1f}" if vix_price else "N/A"
    vix_color = "#e74c3c" if vix_price and vix_price > 20 else "#2ecc71"
    vix_label = "ELEVATED" if vix_price and vix_price > 20 else "CALM"

    # 10-Year Treasury
    tny_price, _, _ = fetch("^TNX")
    tny_str = f"{tny_price:.2f}%" if tny_price else "N/A"

    pulse_cells += f"""
        <td style="padding:16px 20px;text-align:center;border-right:1px solid #222;">
          <div style="color:#aaa;font-size:0.8em;margin-bottom:4px;">VIX (Fear Index)</div>
          <div style="font-size:1.3em;font-weight:bold;color:{vix_color};">{vix_str}</div>
          <div style="color:{vix_color};font-size:0.9em;margin-top:4px;">{vix_label}</div>
        </td>
        <td style="padding:16px 20px;text-align:center;">
          <div style="color:#aaa;font-size:0.8em;margin-bottom:4px;">10-Year Yield</div>
          <div style="font-size:1.3em;font-weight:bold;color:#fff;">{tny_str}</div>
          <div style="color:#aaa;font-size:0.9em;margin-top:4px;">US Treasury</div>
        </td>"""

    sections.append(f"""
    <div style="margin-bottom:36px;">
      {section_header("📈 Market Pulse")}
      <table style="width:100%;border-collapse:collapse;background:#1a1a1a;border-radius:8px;overflow:hidden;">
        <tr>{pulse_cells}</tr>
      </table>
    </div>""")

    # ── 2. MACRO DASHBOARD ────────────────────────────────────────────────────
    print("Fetching macro data...")
    macro_rows = ""
    for ticker, label in MACRO.items():
        price, chg, pct = fetch(ticker)
        ar, col = arrow_color(pct)
        if price is None:
            continue
        if ticker == "BTC-USD":
            price_str = f"${price:,.0f}"
        elif ticker == "DX-Y.NYB":
            price_str = f"{price:.2f}"
        elif ticker == "GC=F":
            price_str = f"${price:,.0f}/oz"
        elif ticker == "CL=F":
            price_str = f"${price:.2f}/bbl"
        else:
            price_str = f"${price:,.2f}"

        macro_rows += f"""
        <tr style="border-bottom:1px solid #222;">
          <td style="padding:10px 14px;font-weight:bold;color:#ddd;">{label}</td>
          <td style="padding:10px 14px;color:#fff;">{price_str}</td>
          <td style="padding:10px 14px;color:{col};">{ar} {abs(chg):.2f} ({abs(pct):.2f}%)</td>
        </tr>"""

    sections.append(f"""
    <div style="margin-bottom:36px;">
      {section_header("🌍 Macro Dashboard")}
      <table style="width:100%;border-collapse:collapse;background:#1a1a1a;border-radius:8px;overflow:hidden;">
        <tr style="background:#111;color:#666;font-size:0.8em;">
          <th style="padding:8px 14px;text-align:left;">Asset</th>
          <th style="padding:8px 14px;text-align:left;">Price</th>
          <th style="padding:8px 14px;text-align:left;">Today</th>
        </tr>
        {macro_rows}
      </table>
    </div>""")

    # ── 3. SECTOR SCORECARD ───────────────────────────────────────────────────
    print("Fetching sector data...")
    sector_data = []
    for ticker, label in SECTORS.items():
        price, chg, pct = fetch(ticker)
        if pct is not None:
            sector_data.append((label, pct))

    sector_data.sort(key=lambda x: x[1], reverse=True)

    sector_rows = ""
    for label, pct in sector_data:
        ar, col = arrow_color(pct)
        bar_width = min(abs(pct) * 8, 100)
        bar_color = "#2ecc71" if pct >= 0 else "#e74c3c"
        sector_rows += f"""
        <tr style="border-bottom:1px solid #1a1a1a;">
          <td style="padding:9px 14px;color:#ccc;font-size:0.9em;">{label}</td>
          <td style="padding:9px 14px;color:{col};font-weight:bold;">{ar} {abs(pct):.2f}%</td>
          <td style="padding:9px 14px;width:120px;">
            <div style="background:#111;border-radius:3px;height:6px;">
              <div style="background:{bar_color};width:{bar_width}%;height:6px;border-radius:3px;"></div>
            </div>
          </td>
        </tr>"""

    sections.append(f"""
    <div style="margin-bottom:36px;">
      {section_header("🗂 Sector Scorecard")}
      <table style="width:100%;border-collapse:collapse;background:#161616;border-radius:8px;overflow:hidden;">
        <tr style="background:#111;color:#666;font-size:0.8em;">
          <th style="padding:8px 14px;text-align:left;">Sector</th>
          <th style="padding:8px 14px;text-align:left;">Change</th>
          <th style="padding:8px 14px;text-align:left;">Strength</th>
        </tr>
        {sector_rows}
      </table>
    </div>""")

    # ── 4. WATCHLIST ALERTS ───────────────────────────────────────────────────
    print("Checking watchlist...")
    watchlist_rows = ""
    in_zone_count = 0
    for ticker in WATCHLIST:
        try:
            stock     = yf.Ticker(ticker)
            fast      = stock.fast_info
            price     = round(fast.last_price, 2)
            year_high = round(fast.year_high, 2)
            pct       = round(((price - year_high) / year_high) * 100, 1)
            _, day_chg, day_pct = fetch(ticker)
            ar, col = arrow_color(day_pct)

            in_zone = -35 <= pct <= -18
            status  = "🟢 In Zone" if in_zone else "⚪ Watch"
            zone_color = "#2ecc71" if in_zone else "#555"
            if in_zone:
                in_zone_count += 1

            day_str = f"{ar} {abs(day_pct):.2f}%" if day_pct is not None else "—"
            watchlist_rows += f"""
            <tr style="border-bottom:1px solid #1a1a1a;">
              <td style="padding:10px 14px;font-weight:bold;color:#fff;">{ticker}</td>
              <td style="padding:10px 14px;color:#ddd;">${price:,.2f}</td>
              <td style="padding:10px 14px;color:{col};">{day_str}</td>
              <td style="padding:10px 14px;color:#aaa;">${year_high:,.2f}</td>
              <td style="padding:10px 14px;color:#aaa;">{pct}%</td>
              <td style="padding:10px 14px;color:{zone_color};font-weight:bold;">{status}</td>
            </tr>"""
        except Exception:
            continue

    zone_note = f'<p style="color:#2ecc71;font-size:0.9em;margin-bottom:12px;">🟢 {in_zone_count} stock(s) currently in the options entry zone.</p>' if in_zone_count else '<p style="color:#666;font-size:0.9em;margin-bottom:12px;">No stocks in the options entry zone today.</p>'

    sections.append(f"""
    <div style="margin-bottom:36px;">
      {section_header("🎯 Watchlist Alerts")}
      <p style="color:#666;font-size:0.85em;margin-bottom:8px;">🟢 In Zone = pulled back 18–35% from 52w high — options entry range</p>
      {zone_note}
      <table style="width:100%;border-collapse:collapse;background:#161616;border-radius:8px;overflow:hidden;">
        <tr style="background:#111;color:#666;font-size:0.8em;">
          <th style="padding:8px 14px;text-align:left;">Ticker</th>
          <th style="padding:8px 14px;text-align:left;">Price</th>
          <th style="padding:8px 14px;text-align:left;">Today</th>
          <th style="padding:8px 14px;text-align:left;">52w High</th>
          <th style="padding:8px 14px;text-align:left;">From High</th>
          <th style="padding:8px 14px;text-align:left;">Signal</th>
        </tr>
        {watchlist_rows}
      </table>
    </div>""")

    # ── 5. WATCHLIST NEWS ─────────────────────────────────────────────────────
    print("Fetching news...")
    news_html = ""
    for ticker in WATCHLIST:
        company_name, headlines = get_news(ticker)
        if not headlines:
            continue
        items = "".join([
            f'<li style="margin-bottom:8px;color:#bbb;line-height:1.5;">'
            f'<span style="color:#666;font-size:0.8em;">{hl["source"]} · {hl["published"]}</span><br>'
            f'<span style="color:#ddd;">{hl["title"]}</span></li>'
            for hl in headlines
        ])
        news_html += f"""
        <div style="margin-bottom:24px;padding:16px;background:#161616;border-radius:8px;border-left:3px solid #cc0000;">
          <div style="color:#ff6666;font-weight:bold;margin-bottom:10px;">{ticker} — {company_name}</div>
          <ul style="padding-left:16px;margin:0;">{items}</ul>
        </div>"""

    sections.append(f"""
    <div style="margin-bottom:36px;">
      {section_header("📰 Watchlist News")}
      {news_html}
    </div>""")

    # ── 6. QUOTE OF THE DAY ───────────────────────────────────────────────────
    quote, author = random.choice(QUOTES)
    sections.append(f"""
    <div style="margin-bottom:36px;padding:24px;background:#0d0d0d;border-radius:8px;border:1px solid #1a1a1a;text-align:center;">
      {section_header("💡 Quote of the Day")}
      <p style="color:#ccc;font-style:italic;font-size:1.05em;line-height:1.7;margin:0 0 12px 0;">"{quote}"</p>
      <p style="color:#cc0000;font-size:0.9em;margin:0;">— {author}</p>
    </div>""")

    # ── ASSEMBLE ──────────────────────────────────────────────────────────────
    body = "\n".join(sections)
    return f"""
    <div style="background:#0a0a0a;color:#f0f0f0;font-family:Georgia,serif;max-width:680px;margin:0 auto;padding:40px 24px;">
      <div style="text-align:center;margin-bottom:40px;border-bottom:2px solid #cc0000;padding-bottom:28px;">
        <div style="color:#cc0000;font-size:0.75em;letter-spacing:4px;margin-bottom:8px;text-transform:uppercase;">Daily Intelligence</div>
        <h1 style="color:#fff;letter-spacing:4px;margin:0;font-size:2em;">MORNING BRIEFING</h1>
        <p style="color:#666;margin-top:10px;font-style:italic;font-size:0.9em;">{today}</p>
      </div>
      {body}
      <div style="text-align:center;color:#333;font-size:0.75em;margin-top:40px;border-top:1px solid #1a1a1a;padding-top:20px;line-height:1.8;">
        Automated · Yahoo Finance · NewsAPI<br>
        Not financial advice. Do your own research.
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
