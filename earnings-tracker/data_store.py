"""Local storage for watchlist data — one JSON file per ticker, no database.

A file per ticker rather than one big file means adding or refreshing one
company never touches another's data, and you can delete a ticker just by
deleting its file.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).parent / "watchlist_data"


def _path(ticker):
    return DATA_DIR / f"{ticker.upper()}.json"


def save_ticker(ticker, quarters):
    """Writes a ticker's quarterly history to disk with a refresh timestamp."""
    DATA_DIR.mkdir(exist_ok=True)
    payload = {
        "ticker": ticker.upper(),
        "last_updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "quarters": quarters,  # most recent first
    }
    _path(ticker).write_text(json.dumps(payload, indent=2))
    return payload


def load_ticker(ticker):
    """Returns the stored payload for a ticker, or None if it isn't tracked."""
    p = _path(ticker)
    if not p.exists():
        return None
    return json.loads(p.read_text())


def ticker_exists(ticker):
    return _path(ticker).exists()


def list_watchlist():
    """All tracked tickers, alphabetical. Skips dotfiles — sec_data.py keeps
    its CIK lookup cache in this same folder, and a leading '.' marks it as
    infrastructure rather than a watchlist entry (caught by testing: it was
    showing up as a phantom ticker before this filter existed)."""
    if not DATA_DIR.exists():
        return []
    return sorted(p.stem for p in DATA_DIR.glob("*.json") if not p.name.startswith("."))


def remove_ticker(ticker):
    p = _path(ticker)
    if p.exists():
        p.unlink()
        return True
    return False
