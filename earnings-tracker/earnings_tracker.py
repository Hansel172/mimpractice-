#!/usr/bin/env python3
"""Personal earnings intelligence — run from the terminal.

  python earnings_tracker.py add TICKER      add a company, pull its history
  python earnings_tracker.py analyze TICKER  compare latest quarter to the baseline
  python earnings_tracker.py monitor         who on your watchlist reports in 14 days
  python earnings_tracker.py report          full analysis for anyone who just reported

No API key. Everything comes from SEC EDGAR (the companies' own filings)
and Nasdaq's public earnings calendar.
"""

import sys

import data_store
import sec_data
from red_flag_detector import detect_red_flags


def _pct_change(new, old):
    if old in (None, 0) or new is None:
        return None
    return (new - old) / abs(old) * 100


def _fmt_money(v):
    if v is None:
        return "n/a"
    return f"${v:,.0f}"


def _fmt_pct(v, signed=True):
    if v is None:
        return "n/a"
    return f"{v:+.1f}%" if signed else f"{v:.1f}%"


# ── add ────────────────────────────────────────────────────────────────────
def cmd_add(ticker):
    ticker = ticker.upper()
    print(f"Looking up {ticker} on SEC EDGAR...")

    cik = sec_data.get_cik(ticker)
    if not cik:
        print(f"\n'{ticker}' isn't in SEC's list of registered tickers. "
              f"Check the spelling — this only covers US-listed companies "
              f"that file with the SEC.")
        return

    print(f"Found it (CIK {cik}). Pulling quarterly financials...")
    quarters = sec_data.get_quarterly_financials(ticker, num_quarters=12)

    if quarters is None:
        print(f"\nCouldn't find any filings for {ticker}.")
        return
    if not quarters:
        print(f"\n{ticker} is SEC-registered but doesn't report financials in the "
              f"standard format this tool reads (common for some ETFs, trusts, "
              f"and foreign filers). Try a different ticker.")
        return

    data_store.save_ticker(ticker, quarters)
    oldest, newest = quarters[-1]["period_end"], quarters[0]["period_end"]
    print(f"\nSaved {len(quarters)} quarters for {ticker} ({oldest} to {newest}).")
    print(f"Run 'python earnings_tracker.py analyze {ticker}' any time to see the report.")


# ── analyze ──────────────────────────────────────────────────────────────
def _classify_metric(name, change, good_is_positive=True, ugly_threshold=None):
    """Sorts one metric's change into good / bad / ugly for the summary
    sections. `ugly_threshold` is the magnitude (in the same units as
    `change`) past which a bad number becomes an alarming one."""
    if change is None:
        return None
    is_good = (change > 0) if good_is_positive else (change < 0)
    if is_good:
        return ("good", f"{name}: {_fmt_pct(change)}")
    if ugly_threshold is not None and abs(change) >= ugly_threshold:
        return ("ugly", f"{name}: {_fmt_pct(change)}")
    return ("bad", f"{name}: {_fmt_pct(change)}")


def cmd_analyze(ticker):
    ticker = ticker.upper()
    stored = data_store.load_ticker(ticker)
    if not stored:
        print(f"{ticker} isn't on your watchlist yet. Run "
              f"'python earnings_tracker.py add {ticker}' first.")
        return

    quarters = stored["quarters"]
    if len(quarters) < 2:
        print(f"Only {len(quarters)} quarter(s) stored for {ticker} — need at "
              f"least 2 to compare. Try again after the next earnings report.")
        return

    cur, prev = quarters[0], quarters[1]
    good, bad, ugly = [], [], []

    for label, key, ugly_at in [
        ("Revenue growth", "revenue", 10),
        ("Gross margin",   None, None),   # handled separately — it's already a % change
        ("Net income",     "net_income", 20),
        ("EPS (diluted)",  "eps_diluted", 20),
        ("Free cash flow", "free_cash_flow", None),
        ("Cash on hand",   "cash", 20),
    ]:
        if key is None:
            continue
        chg = _pct_change(cur.get(key), prev.get(key))
        # Debt and cash read "good" in opposite directions from growth metrics.
        good_dir = key != "debt"
        result = _classify_metric(label, chg, good_is_positive=good_dir, ugly_threshold=ugly_at)
        if result:
            (good if result[0] == "good" else bad if result[0] == "bad" else ugly).append(result[1])

    # Debt: shrinking or flat is good; growing is bad, and >15% is the same
    # threshold the red-flag detector uses, so it lands in the same bucket here.
    debt_chg = _pct_change(cur.get("debt"), prev.get("debt"))
    if debt_chg is not None:
        result = _classify_metric("Debt", debt_chg, good_is_positive=False, ugly_threshold=15)
        (good if result[0] == "good" else bad if result[0] == "bad" else ugly).append(result[1])

    # Gross margin: compare percentage-point change, not percent change of a percent.
    gm_cur, gm_prev = cur.get("gross_margin_pct"), prev.get("gross_margin_pct")
    if gm_cur is not None and gm_prev is not None:
        pts = gm_cur - gm_prev
        line = f"Gross margin: {pts:+.1f} points ({gm_prev:.1f}% -> {gm_cur:.1f}%)"
        bucket = "good" if pts > 0 else "ugly" if pts <= -2 else "bad"
        (good if bucket == "good" else bad if bucket == "bad" else ugly).append(line)

    flags = detect_red_flags(quarters)

    print(f"\n{'=' * 60}")
    print(f"  EARNINGS ANALYSIS — {ticker}")
    print(f"  Quarter ending {cur['period_end']}  (vs. {prev['period_end']})")
    print(f"{'=' * 60}")

    print(f"\nTHE GOOD")
    print("-" * 40)
    for line in good:
        print(f"  + {line}")
    if not good:
        print("  (nothing stood out this quarter)")

    print(f"\nTHE BAD")
    print("-" * 40)
    for line in bad:
        print(f"  - {line}")
    if not bad:
        print("  (nothing here)")

    print(f"\nTHE UGLY")
    print("-" * 40)
    for line in ugly:
        print(f"  ! {line}")
    if not ugly:
        print("  (nothing alarming)")

    print(f"\nRED FLAGS")
    print("-" * 40)
    if not flags:
        print("  None detected.")
    else:
        for f in sorted(flags, key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["severity"]]):
            print(f"  [{f['severity'].upper()}] {f['flag']}")
            print(f"     {f['detail']}")

    # Best-effort: did this quarter beat or miss consensus? Nasdaq's calendar
    # is keyed by report date, which isn't always exactly the period end, so
    # this is informational and silently skipped if it can't be matched.
    surprise = sec_data.get_earnings_surprise(ticker, cur["period_end"])
    if surprise and surprise.get("eps"):
        print(f"\nANALYST REACTION (Nasdaq)")
        print("-" * 40)
        print(f"  EPS: {surprise.get('eps', 'n/a')}  |  "
              f"Consensus: {surprise.get('epsForecast', 'n/a')}  |  "
              f"Surprise: {surprise.get('surprise', 'n/a')}")

    print()


# ── monitor ──────────────────────────────────────────────────────────────
def cmd_monitor():
    watchlist = data_store.list_watchlist()
    if not watchlist:
        print("Your watchlist is empty. Add a company first: "
              "python earnings_tracker.py add TICKER")
        return

    n = len(watchlist)
    print(f"Checking the next 14 days for {n} compan{'y' if n == 1 else 'ies'} on your watchlist...")
    calendar = sec_data.get_earnings_calendar(days_ahead=14)

    watch_set = set(watchlist)
    hits = []
    for d, rows in calendar.items():
        for row in rows:
            sym = row.get("symbol", "").upper()
            if sym in watch_set:
                hits.append((d, sym, row.get("time", "")))

    print(f"\n{'=' * 50}")
    print("  UPCOMING EARNINGS — NEXT 14 DAYS")
    print(f"{'=' * 50}")
    if not hits:
        print("  Nothing on your watchlist reports in this window.")
    else:
        for d, sym, t in sorted(hits):
            print(f"  {d}   {sym:<8} {t or ''}")
    print()


# ── report ───────────────────────────────────────────────────────────────
def cmd_report():
    watchlist = data_store.list_watchlist()
    if not watchlist:
        print("Your watchlist is empty. Add a company first: "
              "python earnings_tracker.py add TICKER")
        return

    print(f"Checking which of {len(watchlist)} companies reported in the last 7 days...")
    recent = sec_data.get_recent_reports(watchlist, days_back=7)

    if not recent:
        print("\nNo one on your watchlist has reported in the last 7 days.")
        return

    print(f"\n{len(recent)} compan{'y has' if len(recent) == 1 else 'ies have'} "
          f"reported: {', '.join(recent)}\n")

    for ticker, info in recent.items():
        print(f"Refreshing {ticker} (reported {info['date']})...")
        quarters = sec_data.get_quarterly_financials(ticker, num_quarters=12)
        if quarters:
            data_store.save_ticker(ticker, quarters)
        cmd_analyze(ticker)


# ── entry point ──────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "add" and len(sys.argv) == 3:
        cmd_add(sys.argv[2])
    elif cmd == "analyze" and len(sys.argv) == 3:
        cmd_analyze(sys.argv[2])
    elif cmd == "monitor" and len(sys.argv) == 2:
        cmd_monitor()
    elif cmd == "report" and len(sys.argv) == 2:
        cmd_report()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
