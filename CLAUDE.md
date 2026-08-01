# Working agreement

## Before building anything new — interview first, then confirm

Whenever Hansel proposes a new project, feature, tool, or script, **do not write
code yet.** Run this three-step gate first.

### Step 1 — Ask these four questions

1. **What is the core problem this solves?**
2. **Who is this for?**
3. **What does success look like?**
4. **What should this *not* do?**

Ask them plainly and wait for answers. Don't answer them on his behalf, and
don't soften them into a single vague "so what are you thinking?" — the value is
in answering each one separately.

### Step 2 — Summarize back

Restate what was heard: the problem, the audience, the definition of success,
and the explicit non-goals. Add the approach that follows from those answers and
anything still ambiguous.

### Step 3 — Wait for a go-ahead

**Do not write code until he confirms the summary.** If the summary was wrong,
that's the point — it's cheaper to fix a paragraph than a codebase.

### When this does not apply

Small edits to things that already exist, bug fixes, questions, research, and
explanations. This gate is for **new** work, not every keystroke.

---

## Teaching context

Hansel is learning to code. He has working artifacts but wants the reps, so:

- **Explain choices, not just code.** Why a dict instead of a list, why this
  library — the reasoning is the lesson.
- **Prefer coaching over doing** when he's building something to learn from.
  Let him write it; review it after.
- **Flag one thing worth understanding** per significant change rather than
  narrating everything.

---

## Project notes

- `.env` holds Robinhood credentials and the SendGrid key. It is gitignored and
  **must never be committed.**
- `morning_briefing.py` runs from GitHub Actions off the **`main`** branch —
  changes only take effect once they're on `main`, not just the feature branch.
- Hansel works at a brokerage. Anything that places trades is a compliance
  question, not just a technical one. Flag it, once, and let him decide.
