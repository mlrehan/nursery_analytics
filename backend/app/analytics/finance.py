"""Financial & Billing analytics."""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.common import Scope, fetch_df, gauge, kpi, month_labels, pct, safe_div


async def compute(db: AsyncSession, scope: Scope) -> dict:
    today = dt.date.today()
    month_start = today.replace(day=1)
    p = scope.params
    sc = scope.site_clause()

    inv = await fetch_df(
        db,
        f"""SELECT i.id, i.period_month, i.issue_date, i.due_date, i.amount, i.funding_amount,
                   i.discount_amount, i.status, i.paid_date, c.first_name, c.last_name,
                   r.room_type
            FROM fact_invoice i
            JOIN dim_child c ON c.id = i.child_id
            LEFT JOIN dim_room r ON r.id = c.room_id
            WHERE 1=1 {scope.site_clause('i')}""",
        p,
    )
    if inv.empty:
        return _empty()

    inv["amount"] = inv["amount"].astype(float)
    inv["period_month"] = pd.to_datetime(inv["period_month"]).dt.date

    win = scope.window_days
    win_lbl = f"last {win} days"
    billed_mtd = float(inv.loc[inv["period_month"] == month_start, "amount"].sum())

    # collected + payment success over the selected period
    pay = await fetch_df(
        db,
        f"""SELECT amount, success, payment_date, is_refund FROM fact_payment
            WHERE 1=1 {sc} AND payment_date >= :dwin""",
        {**p, "dwin": today - dt.timedelta(days=win)},
    )
    collected = float(pay.loc[pay["success"] & ~pay["is_refund"], "amount"].astype(float).sum()) if not pay.empty else 0.0
    paid_attempts = pay.loc[~pay["is_refund"]] if not pay.empty else pay
    success_rate = pct(safe_div(int(paid_attempts["success"].sum()), len(paid_attempts)) * 100) if not paid_attempts.empty else 100.0

    outstanding = inv[inv["status"].isin(["unpaid", "overdue", "partial"])]
    arrears = float(outstanding["amount"].sum())

    # paid vs unpaid pie
    status_counts = inv["status"].value_counts()
    pie = {"data": [{"name": s.capitalize(), "value": int(c)} for s, c in status_counts.items()]}

    # aged receivables buckets
    aged = {"categories": ["0-30d", "31-60d", "61-90d", "90d+"], "series": [{"name": "Outstanding £", "data": [0, 0, 0, 0]}]}
    if not outstanding.empty:
        due = pd.to_datetime(outstanding["due_date"]).dt.date
        age_days = np.array([(today - d).days for d in due])
        buckets = pd.cut(age_days, bins=[-9999, 30, 60, 90, 999999],
                         labels=["0-30d", "31-60d", "61-90d", "90d+"])
        grp = outstanding.assign(bucket=buckets).groupby("bucket", observed=False)["amount"].sum()
        aged["series"][0]["data"] = [round(float(grp.get(b, 0)), 2) for b in aged["categories"]]

    # revenue breakdown stacked (last 12 months): net private + funding + discount
    months = sorted(inv["period_month"].unique())[-12:]
    breakdown = {"categories": month_labels(list(months)),
                 "series": [{"name": "Net Fees", "data": []},
                            {"name": "Funding", "data": []},
                            {"name": "Discounts", "data": []}],
                 "stack": True}
    rev_trend = {"x": month_labels(list(months)), "series": [{"name": "Billed £", "data": []}]}
    for m in months:
        sub = inv[inv["period_month"] == m]
        breakdown["series"][0]["data"].append(round(float(sub["amount"].sum()), 2))
        breakdown["series"][1]["data"].append(round(float(sub["funding_amount"].astype(float).sum()), 2))
        breakdown["series"][2]["data"].append(round(float(sub["discount_amount"].astype(float).sum()), 2))
        rev_trend["series"][0]["data"].append(round(float(sub["amount"].sum()), 2))

    # profit per room type (current month billed as proxy contribution)
    per_room = {"categories": [], "series": [{"name": "Revenue £", "data": []}]}
    cur_m = inv[inv["period_month"] == month_start]
    if not cur_m.empty:
        grp = cur_m.groupby("room_type")["amount"].sum()
        for rt in ["baby", "toddler", "preschool"]:
            per_room["categories"].append(rt.capitalize())
            per_room["series"][0]["data"].append(round(float(grp.get(rt, 0)), 2))

    # funding mix + revenue per child (UK free-hours context)
    ch = await fetch_df(
        db, f"SELECT funding_type, COUNT(*) AS n FROM dim_child WHERE status='active' {sc} GROUP BY funding_type", p)
    funding_labels = {"private": "Private", "funded_15": "15h funded", "funded_30": "30h funded"}
    funding_pie = {"data": [{"name": funding_labels.get(r["funding_type"], r["funding_type"] or "Private"),
                             "value": int(r["n"])} for _, r in ch.iterrows()]} if not ch.empty else {"data": []}
    active_count = int(ch["n"].sum()) if not ch.empty else 0
    rev_per_child = round(billed_mtd / active_count, 2) if active_count else 0

    # late payment alerts table
    overdue = inv[inv["status"] == "overdue"].copy()
    rows = []
    if not overdue.empty:
        overdue["child"] = overdue["first_name"] + " " + overdue["last_name"]
        overdue = overdue.sort_values("amount", ascending=False).head(15)
        for _, r in overdue.iterrows():
            days_over = (today - r["due_date"]).days if isinstance(r["due_date"], dt.date) else 0
            rows.append([r["child"], f"£{float(r['amount']):,.2f}", f"{days_over}d", r["status"].capitalize()])
    late_table = {"columns": ["Child", "Amount", "Overdue", "Status"], "rows": rows}

    return {
        "fin.billed": kpi(round(billed_mtd, 2), "Billed This Month", unit="£", sub="this calendar month"),
        "fin.collected": kpi(round(collected, 2), "Collected", unit="£", sub=win_lbl),
        "fin.arrears": kpi(round(arrears, 2), "Outstanding Debt", unit="£", sub="as of today",
                           status="warn" if arrears > 0 else "ok"),
        "fin.success_rate": gauge(success_rate, "Payment Success"),
        "fin.paid_unpaid": pie,
        "fin.aged": aged,
        "fin.breakdown": breakdown,
        "fin.per_room": per_room,
        "fin.late_alerts": late_table,
        "fin.funding": funding_pie,
        "fin.rev_per_child": kpi(rev_per_child, "Revenue per Child", unit="£", accent="emerald", sub="monthly average"),
        "fin.revenue_trend": rev_trend,
        "_billed_mtd": round(billed_mtd, 2), "_arrears": round(arrears, 2),
        "_rev_trend": rev_trend,
    }


def _empty() -> dict:
    z = {"value": 0, "label": "", "unit": "£"}
    return {
        "fin.billed": z, "fin.collected": z, "fin.arrears": z,
        "fin.success_rate": gauge(0, "Payment Success"),
        "fin.paid_unpaid": {"data": []}, "fin.aged": {"categories": [], "series": []},
        "fin.breakdown": {"categories": [], "series": [], "stack": True},
        "fin.per_room": {"categories": [], "series": []},
        "fin.late_alerts": {"columns": ["Child", "Amount", "Overdue", "Status"], "rows": []},
        "fin.funding": {"data": []},
        "fin.rev_per_child": {"value": 0, "label": "Revenue per Child", "unit": "£"},
        "fin.revenue_trend": {"x": [], "series": [{"name": "Billed £", "data": []}]},
        "_billed_mtd": 0, "_arrears": 0, "_rev_trend": {"x": [], "series": [{"name": "Billed £", "data": []}]},
    }
