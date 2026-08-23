# Earnings Tracker

Tracks earnings for companies you follow, and flags things worth a second
look when a new quarter comes in.

**No API key.** Everything comes from SEC EDGAR (the companies' own filings)
and Nasdaq's public earnings calendar — both free, no signup.

## Setup

```bash
cd earnings-tracker
pip install -r requirements.txt
```

## The four commands

**Add a company to your watchlist:**
```bash
python earnings_tracker.py add NVDA
```
Pulls 12 quarters of history and saves it to `watchlist_data/NVDA.json`.
Run this once per company before analyzing it.

**Analyze the latest quarter against the stored baseline:**
```bash
python earnings_tracker.py analyze NVDA
```
Prints a report in four sections — THE GOOD, THE BAD, THE UGLY, and RED
FLAGS — comparing the most recent quarter to the one before it.

**See who's reporting soon:**
```bash
python earnings_tracker.py monitor
```
Checks the next 14 days against your whole watchlist.

**Catch up on anyone who just reported:**
```bash
python earnings_tracker.py report
```
Finds anyone on your watchlist who reported in the last 7 days, refreshes
their data, and runs the full analysis on each.

## What counts as a red flag

- Gross margin down more than 2 points quarter over quarter
- Operating expenses growing faster than revenue for two straight quarters
- Free cash flow flipping negative after being positive
- Net income falling while revenue is still growing
- Cash dropping more than 20% in one quarter (worse if debt rose at the same time)
- Debt rising more than 15% in one quarter

## What this can't do

**No forward guidance.** SEC filings report what already happened, not what
a company says will happen next quarter — that lives in earnings calls and
press releases, not the financial statements this tool reads. `analyze`
does show the analyst consensus beat/miss when Nasdaq's calendar has it,
which is the closest available substitute.

**Large, established US companies work best.** SEC's XBRL data is cleanest
for big filers. Very small companies, foreign private issuers, and some
ETFs/trusts don't tag their financials the same way and may come back
mostly empty — `add` will tell you plainly if that happens rather than
guessing.

## Two things worth knowing about how the numbers are built

**Q4 is derived, not filed directly.** Companies almost never file a
standalone fourth-quarter report — only the full year, in the 10-K. Q4 is
calculated as `full year − Q1 − Q2 − Q3` wherever those three are already
known. This works correctly for dollar figures (revenue, net income, cash
flow) because they add up across quarters. It does **not** work for EPS,
since EPS is a per-share ratio and share counts shift quarter to quarter —
so a derived Q4's EPS is left blank rather than shown as a wrong number.

**Tags can change over time.** Companies occasionally switch which SEC
label they file a number under — Microsoft, for instance, reported revenue
under `Revenues` only through 2010, then switched to a longer label
(`RevenueFromContractWithCustomerExcludingAssessedTax`) from 2016 onward.
This tool checks every common label for a concept and merges what it finds,
so a company's older or newer filings are both counted rather than only
whichever tag happens to be tried first.

## The mobile app

There's also a real page — the same analysis, but as something you open on
your phone rather than the terminal. It lives at `docs/earnings/` and
publishes to GitHub Pages, refreshed automatically on weekdays after market
close by `.github/workflows/earnings_refresh.yml`.

**Which companies show up** is controlled by `watchlist.txt` — one entry per
line, ticker followed by a short description of the business (e.g. `NVDA
Designs GPUs and AI chips...`), which the app displays on each card. A
different, deliberately public list from the CLI's own `watchlist_data/`
(see Privacy below). The CLI's `analyze` command also looks up a matching
description here if one exists, purely as a bonus — it works fine without one.

**To rebuild it by hand:**
```bash
python earnings-tracker/scripts/build_public.py
```
This reads `watchlist.txt`, runs the exact same comparison logic the CLI
uses (`analyzer.py` — one shared function, so the phone app and the terminal
report can never quietly disagree with each other), and writes
`docs/earnings/data.json`.

**Add to your home screen:** open the page in Safari or Chrome, then use
"Add to Home Screen." It gets its own icon and opens full-screen, no browser
chrome — same as a normal app. It also works offline, showing whatever was
last loaded.

**Share button:** uses your phone's native share sheet (the same one every
app uses) to send the link via Messages, Mail, or anywhere else. Falls back
to copying the link on a browser that doesn't support it.

Unlike the CLI, there's no separate "judgment" step to keep in sync — every
card is computed mechanically from SEC and Nasdaq data, so the Action can
rebuild the whole page from a clean checkout every run.

**Current watchlist:** NVDA, AAPL, MSFT, SPCX, MU, SNDK, WDC, STX. Edit
`watchlist.txt` and re-run `build_public.py` to change it.

### 12-quarter trend

Each card also draws on the full stored history, not just the latest
quarter versus the one before it:

- A revenue sparkline across every quarter on file (up to 12), with the
  most recent point marked in the card's status color.
- A streak note when it's genuinely informative — "revenue has grown for
  N straight quarters" only appears once N reaches 3, since anything less
  just restates what the quarter-over-quarter comparison above it already
  says.
- "Show all N quarters" expands to the full revenue / gross margin / EPS
  table. EPS reads `n/a` on a derived Q4 for the same reason it does
  elsewhere in this tool — see "Q4 is derived, not filed directly" above.

### App icon

`docs/earnings/icon-source.html` is the editable source — a plain SVG (an
upward sparkline with an endpoint dot, the same motif already used on every
card) rendered to `icon-180.png` / `icon-192.png` / `icon-512.png` via a
browser canvas rather than a design tool, so no new dependency was needed.
To change it: edit the SVG in that file, then regenerate the three PNGs at
their exact pixel sizes (rendering each at its native size directly, rather
than scaling one image down, is what keeps the small one crisp).

## Email alerts

You don't have to remember to open the app — an email goes out only when a
tracked company actually reports a new quarter. Silent every other day.

This reuses the same SendGrid setup as `morning_briefing.py` (one email
pipeline, not two) and runs as part of the same scheduled Action that
refreshes the app. Each run snapshots the previously-published data before
rebuilding, then `send_alerts.py` compares old against new — a ticker whose
latest quarter date changed gets an email; nothing else does.

**To test it by hand:**
```bash
python earnings-tracker/scripts/send_alerts.py path/to/an/older/data.json
```

## Files

| File | What it does |
|---|---|
| `earnings_tracker.py` | The CLI — the four commands above |
| `analyzer.py` | The comparison logic itself — shared by the CLI and the web app |
| `sec_data.py` | Pulls and cleans data from SEC EDGAR and Nasdaq |
| `red_flag_detector.py` | Scans a company's history for the six flags above |
| `data_store.py` | Saves and loads each ticker's data as local JSON (CLI only) |
| `watchlist.txt` | Which companies the *web app* shows — plain, public, committed |
| `scripts/build_public.py` | Builds `docs/earnings/` from `watchlist.txt` |
| `scripts/send_alerts.py` | Emails you only when someone new has reported |
| `watchlist_data/` | Where the *CLI's* tracked companies' data lives (not committed — see below) |

## Privacy

Two different watchlists, two different rules, on purpose:

- **`watchlist_data/*.json`** (the CLI) is gitignored. This is your personal,
  ad hoc research list — whatever you've typed `add TICKER` for — and it's
  nobody's business but yours.
- **`watchlist.txt`** (the web app) is committed and public by design. It's
  a short, deliberate list you chose to publish, and the app itself only
  ever displays public company financials — no personal or account
  information touches it at all, so there's nothing to redact.
