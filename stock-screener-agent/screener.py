import yfinance as yf
from datetime import datetime

# ── CONFIG ────────────────────────────────────────────────────────────────────
TICKERS_FILE = "options_tickers.txt"

# Gate thresholds — adjust these anytime
DRAWDOWN_MIN = -35   # stock must be at least this far below 52w high (%)
DRAWDOWN_MAX = -18   # but not more beaten down than this (%)
MAX_IV       = 60    # implied volatility ceiling — above this, options are expensive
MIN_OI       = 100   # minimum open interest for liquidity
# ─────────────────────────────────────────────────────────────────────────────


def load_tickers():
    with open(TICKERS_FILE) as f:
        return [line.strip().upper() for line in f if line.strip()]


def check_stock(ticker):
    try:
        stock = yf.Ticker(ticker)
        fast  = stock.fast_info
        info  = stock.info

        price      = round(fast.last_price, 2)
        year_high  = round(fast.year_high, 2)
        year_low   = round(fast.year_low, 2)
        market_cap = fast.market_cap
        pe         = info.get("trailingPE")

        pct_from_high = round(((price - year_high) / year_high) * 100, 2)
        pct_from_low  = round(((price - year_low)  / year_low)  * 100, 2)

        return {
            "ticker":       ticker,
            "company":      info.get("shortName", ticker),
            "price":        price,
            "52w_high":     year_high,
            "52w_low":      year_low,
            "pct_from_high": pct_from_high,
            "pct_from_low": pct_from_low,
            "market_cap_b": round(market_cap / 1e9, 1) if market_cap else None,
            "pe":           round(pe, 1) if pe else None,
        }
    except Exception:
        return None


def check_options(ticker, price, year_high):
    try:
        from datetime import timedelta
        stock = yf.Ticker(ticker)
        expirations = stock.options
        leap_exps = [
            e for e in expirations
            if datetime.strptime(e, "%Y-%m-%d") > datetime.now() + timedelta(days=365)
        ]
        if not leap_exps:
            return None

        target_exp = leap_exps[0]
        chain = stock.option_chain(target_exp)
        calls = chain.calls

        # Slightly OTM calls (5–20% above current price)
        candidates = calls[
            (calls["strike"] >= price * 1.05) &
            (calls["strike"] <= price * 1.20)
        ]
        if candidates.empty:
            candidates = calls[calls["strike"] >= price]
        if candidates.empty:
            return None

        best = candidates.loc[candidates["openInterest"].idxmax()]

        iv        = round(best["impliedVolatility"] * 100, 1)
        ask       = round(best["ask"], 2)
        strike    = best["strike"]
        oi        = int(best["openInterest"])
        est_high  = round(ask * (year_high / price) * 1.15, 2)
        opt_depr  = round(((ask - est_high) / est_high) * 100, 1)

        return {
            "expiration": target_exp,
            "strike":     strike,
            "ask":        ask,
            "iv":         iv,
            "oi":         oi,
            "opt_depr":   opt_depr,
        }
    except Exception:
        return None


def run_screener():
    tickers = load_tickers()

    print("=" * 65)
    print(f"  STOCK SCREENER  —  {datetime.now().strftime('%B %d, %Y  %I:%M %p')}")
    print("=" * 65)
    print(f"  Scanning {len(tickers)} tickers...")
    print(f"  Gate 1: Stock drawdown {DRAWDOWN_MAX}% to {DRAWDOWN_MIN}% from 52w high")
    print(f"  Gate 2: LEAP call IV below {MAX_IV}%")
    print(f"  Gate 3: Open interest above {MIN_OI}")
    print("=" * 65)

    passed   = []
    rejected = []

    for ticker in tickers:
        data = check_stock(ticker)
        if not data:
            print(f"  [ERROR]  {ticker} — could not fetch data")
            continue

        pct = data["pct_from_high"]

        # Gate 1: drawdown range
        if not (DRAWDOWN_MIN <= pct <= DRAWDOWN_MAX):
            rejected.append((ticker, f"drawdown {pct}% — outside target range"))
            print(f"  [SKIP ]  {ticker:<6}  {pct:>7.1f}% from high  — not in range")
            continue

        # Gate 2 + 3: options check
        opts = check_options(ticker, data["price"], data["52w_high"])
        if not opts:
            rejected.append((ticker, "no LEAP options available"))
            print(f"  [SKIP ]  {ticker:<6}  {pct:>7.1f}% from high  — no LEAP options")
            continue

        if opts["iv"] > MAX_IV:
            rejected.append((ticker, f"IV {opts['iv']}% too high"))
            print(f"  [SKIP ]  {ticker:<6}  {pct:>7.1f}% from high  — IV {opts['iv']}% too elevated")
            continue

        if opts["oi"] < MIN_OI:
            rejected.append((ticker, f"OI {opts['oi']} too low — illiquid"))
            print(f"  [SKIP ]  {ticker:<6}  {pct:>7.1f}% from high  — OI {opts['oi']} too low")
            continue

        # Passed all gates
        passed.append({**data, **opts})
        print(f"  [PASS ]  {ticker:<6}  {pct:>7.1f}% from high  ✓")

    # ── RESULTS ──────────────────────────────────────────────────────────────
    print()
    print("=" * 65)
    print(f"  RESULTS: {len(passed)} of {len(tickers)} passed all gates")
    print("=" * 65)

    if not passed:
        print("\n  No stocks passed all gates today.")
        print("  Consider widening the drawdown range or IV threshold.\n")
        return

    # Sort by deepest option depreciation (most contracted premium = best entry)
    passed.sort(key=lambda x: x["opt_depr"])

    for i, s in enumerate(passed, 1):
        cap = f"${s['market_cap_b']}B" if s['market_cap_b'] else "N/A"
        pe  = str(s['pe'])            if s['pe']         else "N/A"

        print(f"""
  #{i}  {s['ticker']}  —  {s['company']}
       Market cap: {cap}   PE: {pe}
       Price: ${s['price']}   52w high: ${s['52w_high']}   Drawdown: {s['pct_from_high']}%
       LEAP: {s['expiration']}  ${s['strike']} call @ ${s['ask']}/share
       IV: {s['iv']}%   Open interest: {s['oi']:,}
       Option est. cheaper by: {abs(s['opt_depr'])}% vs high
""")

    print("=" * 65)
    print("  Criteria: Pullback company + contracted premium + liquid options")
    print("  Edit tickers.txt to change your watchlist.")
    print("  Edit screener.py thresholds to tune the gates.")
    print("=" * 65)


if __name__ == "__main__":
    run_screener()
