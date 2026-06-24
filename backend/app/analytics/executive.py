"""Executive Overview — composes signals from the other modules."""
from __future__ import annotations

import datetime as dt

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import compliance, finance, occupancy, staff
from app.analytics.common import Scope, fetch_df, gauge, kpi, linear_forecast


async def compute(db: AsyncSession, scope: Scope) -> dict:
    occ = await occupancy.compute(db, scope)
    fin = await finance.compute(db, scope)
    stf = await staff.compute(db, scope)
    comp = await compliance.compute(db, scope)

    capacity = occ["_capacity"]
    filled = occ["_filled"]
    billed_mtd = fin["_billed_mtd"]
    arrears = fin["_arrears"]
    payroll = stf["staff.payroll"]["value"]

    # overhead (monthly) for scoped sites
    ov = await fetch_df(
        db, f"SELECT COALESCE(SUM(monthly_overhead),0) AS ov FROM dim_site WHERE 1=1 {scope.site_clause()}", scope.params)
    overhead = float(ov["ov"].iloc[0])
    profit = round(billed_mtd - payroll - overhead, 2)

    # revenue trend + 3-month forecast
    rt = fin["_rev_trend"]
    hist = rt["series"][0]["data"]
    rev_trend = {"x": list(rt["x"]), "series": [{"name": "Billed £", "data": list(hist)},
                                                {"name": "Forecast", "data": []}]}
    if hist:
        fc = linear_forecast(hist, 3)
        today = dt.date.today().replace(day=1)
        fut = [(_add_months(today, i + 1)).strftime("%b %y") for i in range(3)]
        rev_trend["x"] += fut
        rev_trend["series"][0]["data"] += [None] * 3
        rev_trend["series"][1]["data"] = [None] * (len(hist) - 1) + [hist[-1]] + [round(v, 2) for v in fc]

    # occupancy by site
    site_occ = await fetch_df(
        db,
        f"""SELECT s.name,
                   (SELECT COUNT(*) FROM dim_child c WHERE c.site_id=s.id AND c.status='active') AS filled,
                   s.capacity
            FROM dim_site s WHERE 1=1 {scope.site_clause('s')} ORDER BY s.name""",
        scope.params,
    )
    site_bar = {"categories": [], "series": [{"name": "Occupancy %", "data": []}]}
    if not site_occ.empty:
        for _, r in site_occ.iterrows():
            site_bar["categories"].append(r["name"])
            site_bar["series"][0]["data"].append(round(float(r["filled"]) / r["capacity"] * 100, 1) if r["capacity"] else 0)

    # alerts summary table
    alerts = []
    if comp["_high_open"]:
        alerts.append(["Compliance", f"{comp['_high_open']} high-severity incident(s) open", "High"])
    if comp["_dbs_expired"]:
        alerts.append(["Staffing", f"{comp['_dbs_expired']} expired DBS check(s)", "High"])
    if stf["_ratio_compliance"] < 100:
        alerts.append(["Staffing", f"Ratio risk in {round(100 - stf['_ratio_compliance'])}% of rooms", "Medium"])
    if arrears > 0:
        alerts.append(["Finance", f"£{arrears:,.0f} outstanding in arrears", "Medium"])
    if not alerts:
        alerts.append(["All clear", "No active alerts", "Low"])

    staff_status = "Safe" if stf["_ratio_compliance"] >= 100 else "At risk"

    return {
        "exec.enrolled": kpi(filled, "Enrolled", sub=f"of {capacity} capacity"),
        "exec.occupancy": gauge(occ["_rate"], "Occupancy"),
        "exec.revenue_mtd": kpi(billed_mtd, "Revenue (MTD)", unit="£"),
        "exec.arrears": kpi(arrears, "Arrears", unit="£", status="warn" if arrears > 0 else "ok"),
        "exec.revenue_trend": rev_trend,
        "exec.profit": kpi(profit, "Profit Estimate (MTD)", unit="£",
                           status="ok" if profit >= 0 else "warn", sub="income − payroll − overhead"),
        "exec.waitlist": kpi(occ["_waitlist"], "Waiting List"),
        "exec.staff_status": kpi(staff_status, "Staff Coverage",
                                 status="ok" if staff_status == "Safe" else "warn"),
        "exec.alerts": {"columns": ["Area", "Detail", "Severity"], "rows": alerts},
        "exec.site_breakdown": site_bar,
    }


def _add_months(d: dt.date, n: int) -> dt.date:
    m = d.month - 1 + n
    return dt.date(d.year + m // 12, m % 12 + 1, 1)
