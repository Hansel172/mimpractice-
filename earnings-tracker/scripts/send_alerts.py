#!/usr/bin/env python3
"""Sends an email only when a tracked company actually reported a new
quarter since the last run. Silent otherwise — this is meant to run on
every scheduled refresh, and most days nothing has changed.

Reuses the same SendGrid setup as morning_briefing.py (SENDGRID_API_KEY,
FROM_EMAIL, TO_EMAIL in .env locally, the same three GitHub repo secrets
in the Action) rather than introducing a second email pipeline.

Usage: send_alerts.py OLD_DATA_JSON
  OLD_DATA_JSON is a snapshot of docs/earnings/data.json taken BEFORE
  build_public.py ran. The workflow is responsible for saving that
  snapshot; this script only compares it against the current (post-
  rebuild) docs/earnings/data.json.
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ROOT.parent
DATA = REPO_ROOT / "docs" / "earnings" / "data.json"
APP_URL = "https://hansel172.github.io/mimpractice-/earnings/"

# The .env with SENDGRID_API_KEY/TO_EMAIL/FROM_EMAIL lives at the repo root
# (same file morning_briefing.py uses), not inside earnings-tracker/.
load_dotenv(REPO_ROOT / ".env")


def load_companies(path):
    p = Path(path)
    if not p.exists():
        return {}
    data = json.loads(p.read_text())
    return {c["ticker"]: c for c in data.get("companies", []) if not c.get("error")}


def find_new_reports(old, new):
    """A ticker counts as 'new' when its most recent period_end differs from
    what was there before — i.e. a fresh quarter has been picked up since
    the last run, not merely that today's rebuild touched the file."""
    changed = []
    for ticker, company in new.items():
        if company.get("insufficient_data"):
            continue
        old_company = old.get(ticker)
        old_period = old_company.get("period_end") if old_company else None
        if company["period_end"] != old_period:
            changed.append(company)
    return changed


def status_for(company):
    flags = company.get("red_flags", [])
    if any(f["severity"] == "high" for f in flags):
        return "FLAGGED", "#ff5252"
    if any(f["severity"] == "medium" for f in flags):
        return "WATCH", "#ff9100"
    return "CLEAN", "#00e676"


def metric_line(m):
    if "change_pts" in m:
        return f"{m['metric']}: {m['change_pts']:+.1f} points"
    return f"{m['metric']}: {m['change_pct']:+.1f}%"


def build_email_html(changed):
    cards = ""
    for c in changed:
        status, color = status_for(c)
        good_items = "".join(f"<li>{metric_line(m)}</li>" for m in c["good"][:4])
        flag_items = "".join(
            f"<li><strong>[{f['severity'].upper()}]</strong> {f['flag']}</li>"
            for f in c["red_flags"]
        )
        cards += f"""
        <div style="margin-bottom:18px;padding:16px 18px;background:#111118;
                    border-radius:8px;border-left:3px solid {color};">
          <div style="color:#e8e8f0;font-weight:700;font-size:16px;">
            {c['ticker']} &mdash; <span style="color:{color};">{status}</span>
          </div>
          <div style="color:#6b6b80;font-size:12px;margin:4px 0 10px;">
            Quarter ending {c['period_end']}
          </div>
          <ul style="color:#e8e8f0;font-size:13px;margin:0 0 8px;padding-left:18px;">
            {good_items or '<li>Nothing stood out</li>'}
          </ul>
          {'<ul style="color:#ff9100;font-size:13px;margin:0;padding-left:18px;">' + flag_items + '</ul>' if flag_items else ''}
        </div>"""

    return f"""
    <div style="background:#0a0a0f;color:#e8e8f0;font-family:sans-serif;
                max-width:560px;margin:0 auto;padding:28px 20px;">
      <h2 style="color:#e8e8f0;margin:0 0 4px;">Earnings Tracker</h2>
      <p style="color:#6b6b80;font-size:13px;margin:0 0 20px;">
        New report{'s' if len(changed) > 1 else ''}: {', '.join(c['ticker'] for c in changed)}
      </p>
      {cards}
      <p style="margin-top:20px;">
        <a href="{APP_URL}" style="color:#448aff;">Open the full app &rarr;</a>
      </p>
    </div>"""


def send(changed):
    sg_key = os.getenv("SENDGRID_API_KEY")
    to_email = os.getenv("TO_EMAIL")
    from_email = os.getenv("FROM_EMAIL")
    if not (sg_key and to_email and from_email):
        print("SendGrid config missing from .env — skipping alert email")
        return

    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=f"Earnings alert: {', '.join(c['ticker'] for c in changed)} reported",
        html_content=build_email_html(changed),
    )
    try:
        resp = SendGridAPIClient(sg_key).send(message)
        print(f"Alert email sent ({resp.status_code})")
    except Exception as e:
        print(f"Failed to send alert email: {e}")


def main():
    if len(sys.argv) != 2:
        print("Usage: send_alerts.py OLD_DATA_JSON", file=sys.stderr)
        return 1

    old = load_companies(sys.argv[1])
    new = load_companies(DATA)
    changed = find_new_reports(old, new)

    if not changed:
        print("No new reports since last run — no alert sent.")
        return 0

    print(f"New report(s): {', '.join(c['ticker'] for c in changed)}")
    send(changed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
