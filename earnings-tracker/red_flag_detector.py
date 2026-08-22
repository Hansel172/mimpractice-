"""Scans a company's quarterly history for warning signs.

Takes the list of quarters sec_data.py produces (most recent first) and
returns a list of flags, each with a severity and a plain-English reason.

One check from the original design is deliberately absent: "guidance cut
vs. prior guidance." SEC financial statements report what already happened,
not what a company says will happen next — forward guidance lives in
earnings-call transcripts and press releases, which aren't part of this
data source. Rather than fake that signal from numbers that don't contain
it, it's left out. earnings_tracker.py surfaces the one guidance-adjacent
thing this data source *can* offer instead: whether the quarter beat or
missed the analyst consensus, from Nasdaq's calendar.
"""


def _pct_change(new, old):
    if old in (None, 0) or new is None:
        return None
    return (new - old) / abs(old) * 100


def detect_red_flags(quarters):
    """quarters: most-recent-first list of quarter dicts.
    Returns a list of {"flag", "severity", "detail"} dicts."""
    flags = []
    if len(quarters) < 2:
        return flags

    cur, prev = quarters[0], quarters[1]

    # 1. Gross margin compression > 2 percentage points, quarter over quarter.
    gm_cur, gm_prev = cur.get("gross_margin_pct"), prev.get("gross_margin_pct")
    if gm_cur is not None and gm_prev is not None:
        drop = gm_prev - gm_cur
        if drop > 2:
            flags.append({
                "flag": "Gross margin compression",
                "severity": "high" if drop > 5 else "medium",
                "detail": (f"Gross margin fell from {gm_prev:.1f}% to {gm_cur:.1f}% "
                           f"({drop:.1f} points). The company is keeping less of every "
                           f"dollar of revenue than it did last quarter — from higher "
                           f"input costs, pricing pressure, or a shift toward lower-margin "
                           f"products."),
            })

    # 2. Operating expenses growing faster than revenue, two quarters running.
    if len(quarters) >= 3:
        q0, q1, q2 = quarters[0], quarters[1], quarters[2]
        rev_g1 = _pct_change(q0.get("revenue"), q1.get("revenue"))
        opex_g1 = _pct_change(q0.get("operating_expenses"), q1.get("operating_expenses"))
        rev_g2 = _pct_change(q1.get("revenue"), q2.get("revenue"))
        opex_g2 = _pct_change(q1.get("operating_expenses"), q2.get("operating_expenses"))
        if None not in (rev_g1, opex_g1, rev_g2, opex_g2) and opex_g1 > rev_g1 and opex_g2 > rev_g2:
            flags.append({
                "flag": "Operating expenses outgrowing revenue",
                "severity": "medium",
                "detail": (f"For two straight quarters, operating costs have grown faster "
                           f"than revenue (most recent: opex {opex_g1:+.1f}% vs. revenue "
                           f"{rev_g1:+.1f}%). If this continues, profitability erodes even "
                           f"while the top line still grows."),
            })

    # 3. Free cash flow flips negative after being positive.
    fcf_cur, fcf_prev = cur.get("free_cash_flow"), prev.get("free_cash_flow")
    if fcf_cur is not None and fcf_prev is not None and fcf_prev > 0 and fcf_cur < 0:
        flags.append({
            "flag": "Free cash flow turned negative",
            "severity": "high",
            "detail": (f"FCF went from +${fcf_prev:,.0f} to -${abs(fcf_cur):,.0f}. The "
                       f"business is now spending more cash than it brings in — worth "
                       f"understanding whether that's a one-time investment or an "
                       f"ongoing problem."),
        })

    # 4. Net income declining while revenue is growing — margin deterioration
    #    disguised by top-line growth.
    rev_chg = _pct_change(cur.get("revenue"), prev.get("revenue"))
    ni_chg = _pct_change(cur.get("net_income"), prev.get("net_income"))
    if rev_chg is not None and ni_chg is not None and rev_chg > 0 and ni_chg < 0:
        flags.append({
            "flag": "Net income falling despite revenue growth",
            "severity": "medium",
            "detail": (f"Revenue rose {rev_chg:.1f}% but net income fell {abs(ni_chg):.1f}%. "
                       f"Growth alone doesn't tell the whole story here — costs are eating "
                       f"more of each new dollar of sales."),
        })

    # 5. Cash declining more than 20% quarter over quarter.
    cash_chg = _pct_change(cur.get("cash"), prev.get("cash"))
    debt_chg = _pct_change(cur.get("debt"), prev.get("debt"))
    if cash_chg is not None and cash_chg < -20:
        # Cash burn combined with rising debt in the same quarter is the more
        # serious pattern — paying for the shortfall by borrowing.
        severe = debt_chg is not None and debt_chg > 0
        flags.append({
            "flag": "Cash reserves dropped sharply",
            "severity": "high" if severe else "medium",
            "detail": (f"Cash and equivalents fell {abs(cash_chg):.1f}% in one quarter."
                       + (f" Debt rose {debt_chg:.1f}% in the same period — spending down "
                          f"cash while also borrowing more is worth a closer look."
                          if severe else "")),
        })

    # 6. Debt increasing more than 15% quarter over quarter.
    if debt_chg is not None and debt_chg > 15:
        flags.append({
            "flag": "Debt load increased significantly",
            "severity": "medium",
            "detail": (f"Total debt rose {debt_chg:.1f}% quarter over quarter. Not "
                       f"automatically bad — could be funding growth — but worth knowing "
                       f"what the new debt is for."),
        })

    return flags
