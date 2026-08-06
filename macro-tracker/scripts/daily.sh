#!/usr/bin/env bash
# Daily refresh. Fetches numbers, rebuilds the bundle, and commits the change
# so the macro view can be diffed over time.
#
# The commit only happens when data/ is actually tracked. In a public repo the
# data files are gitignored (they contain holdings), so this degrades to a
# plain refresh rather than silently doing nothing surprising.
set -euo pipefail

cd "$(dirname "$0")/.."
python3 scripts/refresh.py

if git check-ignore -q data/live.json 2>/dev/null; then
  echo "data/ is gitignored — refreshed but not committed."
  echo "Move this project to a PRIVATE repo to get version history."
  exit 0
fi

if [[ -n "$(git status --porcelain data/)" ]]; then
  git add data/
  git commit -q -m "Data refresh $(date +%Y-%m-%d)"
  echo "Committed."
else
  echo "No change since last refresh."
fi
