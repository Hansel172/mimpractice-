#!/usr/bin/env python3
"""Options screener, same gates as stock-screener-agent/screener.py, but sourced
from Robinhood instead of Yahoo — Yahoo rate-limits this environment to 429.

Gates (unchanged from the original):
  1. Stock is 18-35% below its 52-week high  — pullback, not collapse
  2. A LEAP expiry exists (>= ~1 year out)   — time for the thesis to work
  3. LEAP call IV < 60%                      — premium not already bid up
  4. Open interest > 100                     — you can actually get out
"""
import pickle, pathlib, sys, datetime
sys.path.insert(0, "/home/user/mimpractice-/mcp")
import robin_stocks.robinhood as r
from robin_stocks.robinhood.helper import set_login_state, update_session

DRAWDOWN_MAX = -18   # at least this far below the high
DRAWDOWN_MIN = -35   # but not more broken than this
MAX_IV       = 60
MIN_OI       = 100

TICKERS = ["AAPL","MSFT","NVDA","AMD","GOOGL","META","PLTR",
           "MU","SNDK","WDC","STX","SNDG"]

d = pickle.load(open(pathlib.Path.home()/".tokens"/"robinhood.pickle","rb"))
update_session("Authorization", f'{d["token_type"]} {d["access_token"]}')
set_login_state(True)

today = datetime.date.today()
passed, rejected = [], []

for t in TICKERS:
    try:
        q = r.get_quotes(t)[0]
        price = float(q["last_trade_price"])
        f = r.get_fundamentals(t)[0]
        high = float(f.get("high_52_weeks") or 0)
        if not high:
            rejected.append((t, "no 52w high")); continue

        pct = (price - high) / high * 100

        if not (DRAWDOWN_MIN <= pct <= DRAWDOWN_MAX):
            rejected.append((t, f"{pct:+.1f}% from high — outside {DRAWDOWN_MAX}..{DRAWDOWN_MIN}"))
            print(f"  [skip] {t:<5} {pct:+7.1f}% from high", flush=True)
            continue

        chains = r.get_chains(t) or {}
        exps = sorted(chains.get("expiration_dates", []))
        leaps = [e for e in exps
                 if (datetime.date.fromisoformat(e) - today).days >= 330]
        if not leaps:
            rejected.append((t, "no LEAP expiry")); 
            print(f"  [skip] {t:<5} {pct:+7.1f}% — no LEAP", flush=True)
            continue

        exp = leaps[0]
        chain = r.find_options_by_expiration(t, exp, optionType="call") or []
        # slightly OTM: 5-25% above spot
        cands = []
        for o in chain:
            if not o: continue
            try:
                k = float(o["strike_price"])
                if not (price*1.05 <= k <= price*1.25): continue
                oi = int(float(o.get("open_interest") or 0))
                iv = float(o.get("implied_volatility") or 0) * 100
                ask = float(o.get("ask_price") or 0)
                if ask <= 0: continue
                cands.append({"strike":k,"oi":oi,"iv":iv,"ask":ask,
                              "bid":float(o.get("bid_price") or 0),
                              "delta":o.get("delta")})
            except Exception:
                continue
        if not cands:
            rejected.append((t, "no OTM strikes with a quote"))
            print(f"  [skip] {t:<5} {pct:+7.1f}% — no quotable OTM strikes", flush=True)
            continue

        best = max(cands, key=lambda c: c["oi"])
        why = []
        if best["iv"] > MAX_IV: why.append(f"IV {best['iv']:.0f}% > {MAX_IV}%")
        if best["oi"] < MIN_OI: why.append(f"OI {best['oi']} < {MIN_OI}")
        if why:
            rejected.append((t, " | ".join(why)))
            print(f"  [skip] {t:<5} {pct:+7.1f}% — {' | '.join(why)}", flush=True)
            continue

        passed.append({"t":t,"price":price,"high":high,"pct":pct,"exp":exp,**best})
        print(f"  [PASS] {t:<5} {pct:+7.1f}% from high  ${best['strike']:.0f}c {exp} "
              f"IV {best['iv']:.0f}% OI {best['oi']}", flush=True)
    except Exception as e:
        rejected.append((t, f"error: {str(e)[:80]}"))
        print(f"  [err ] {t:<5} {str(e)[:70]}", flush=True)

print("\n" + "="*66)
print(f"PASSED ALL GATES: {len(passed)} of {len(TICKERS)}")
print("="*66)
for s in sorted(passed, key=lambda x: x["pct"]):
    spread = (s["ask"]-s["bid"])/s["ask"]*100 if s["ask"] else 0
    print(f"\n{s['t']}  ${s['price']:.2f}   52w high ${s['high']:.2f}   {s['pct']:+.1f}%")
    print(f"   LEAP {s['exp']}  ${s['strike']:.0f} call")
    print(f"   bid ${s['bid']:.2f} / ask ${s['ask']:.2f}  (spread {spread:.0f}%)")
    print(f"   IV {s['iv']:.0f}%   OI {s['oi']:,}   delta {s['delta']}")
    print(f"   breakeven ${s['strike']+s['ask']:.2f}  = {(s['strike']+s['ask']-s['price'])/s['price']*100:+.0f}% from spot")

print("\nREJECTED:")
for t, why in rejected:
    print(f"  {t:<6} {why}")
