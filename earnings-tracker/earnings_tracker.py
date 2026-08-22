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
from analyzer import build_analysis


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
def _fmt_metric_line(m):
    if "change_pts" in m:
        return f"{m['metric']}: {m['change_pts']:+.1f} points ({m['from_pct']:.1f}% -> {m['to_pct']:.1f}%)"
    return f"{m['metric']}: {_fmt_pct(m['change_pct'])}"


def cmd_analyze(ticker):
    """Prints the terminal report. All the actual comparison logic lives in
    analyzer.build_analysis() so the CLI and the public web page (built by
    build_public.py) can never quietly drift apart from each other."""
    ticker = ticker.upper()
    stored = data_store.load_ticker(ticker)
    if not stored:
        print(f"{ticker} isn't on your watchlist yet. Run "
              f"'python earnings_tracker.py add {ticker}' first.")
        return

    quarters = stored["quarters"]
    result = build_analysis(ticker, quarters)

    if result["insufficient_data"]:
        n = result["quarters_available"]
        print(f"Only {n} quarter(s) stored for {ticker} — need at least 2 to "
              f"compare. Try again after the next earnings report.")
        return

    if not result["is_quarterly_comparison"]:
        months = round(result["gap_days"] / 30.4)
        print(f"\nNOTE: only {len(quarters)} usable quarter(s) exist for {ticker} in SEC's "
              f"data — common for a recently-public company. The comparison below spans "
              f"{result['gap_days']} days (~{months} months), not one quarter, so treat "
              f"these as longer-term changes, not quarter-over-quarter ones.")

    print(f"\n{'=' * 60}")
    print(f"  EARNINGS ANALYSIS — {ticker}")
    print(f"  Quarter ending {result['period_end']}  (vs. {result['compared_to']})")
    print(f"{'=' * 60}")

    print(f"\nTHE GOOD")
    print("-" * 40)
    for m in result["good"]:
        print(f"  + {_fmt_metric_line(m)}")
    if not result["good"]:
        print("  (nothing stood out this quarter)")

    print(f"\nTHE BAD")
    print("-" * 40)
    for m in result["bad"]:
        print(f"  - {_fmt_metric_line(m)}")
    if not result["bad"]:
        print("  (nothing here)")

    print(f"\nTHE UGLY")
    print("-" * 40)
    for m in result["ugly"]:
        print(f"  ! {_fmt_metric_line(m)}")
    if not result["ugly"]:
        print("  (nothing alarming)")

    print(f"\nRED FLAGS")
    print("-" * 40)
    flags = result["red_flags"]
    if not flags:
        print("  None detected.")
    else:
        for f in sorted(flags, key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["severity"]]):
            print(f"  [{f['severity'].upper()}] {f['flag']}")
            print(f"     {f['detail']}")

    # Best-effort: did this quarter beat or miss consensus? Nasdaq's calendar
    # is keyed by report date, which isn't always exactly the period end, so
    # this is informational and silently skipped if it can't be matched.
    surprise = sec_data.get_earnings_surprise(ticker, result["period_end"])
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
