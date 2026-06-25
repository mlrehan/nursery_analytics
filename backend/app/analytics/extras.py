"""Remaining dashboard modules (nutrition, parent comms, multisite, BI, alerts,
operations, mobile, AI). Compact pandas aggregations over the same fact tables."""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import compliance, finance, occupancy, staff
from app.analytics.common import Scope, fetch_df, gauge, kpi, linear_forecast, pct, safe_div


# ─── Nutrition ────────────────────────────────────────────────────────────────
async def nutrition(db: AsyncSession, scope: Scope) -> dict:
    today = dt.date.today()
    p = scope.params
    sc = scope.site_clause()
    win = scope.window_days
    meals = await fetch_df(
        db, f"SELECT meal_type, intake_pct, allergy_flag, date FROM fact_meal WHERE date >= :dwin {sc}",
        {**p, "dwin": today - dt.timedelta(days=win)})
    allergy = await fetch_df(
        db, f"SELECT COUNT(*) AS n FROM dim_child WHERE allergies IS NOT NULL AND status='active' {sc}", p)
    avg_intake = pct(meals["intake_pct"].astype(float).mean()) if not meals.empty else 0
    by_meal = {"categories": [], "series": [{"name": "Avg Intake %", "data": []}]}
    if not meals.empty:
        grp = meals.groupby("meal_type")["intake_pct"].mean()
        for mt in ["breakfast", "lunch", "snack", "tea"]:
            by_meal["categories"].append(mt.capitalize())
            by_meal["series"][0]["data"].append(pct(grp.get(mt, 0)))
    return {
        "nut.intake": gauge(avg_intake, "Avg Meal Intake"),
        "nut.allergy": kpi(int(allergy["n"].iloc[0]) if not allergy.empty else 0, "Allergy Alerts", status="warn"),
        "nut.meals_logged": kpi(int(len(meals)), "Meals Logged", sub=f"last {win} days"),
        "nut.by_meal": by_meal,
    }


# ─── Parent communication ─────────────────────────────────────────────────────
async def parent_comms(db: AsyncSession, scope: Scope) -> dict:
    today = dt.date.today()
    p = scope.params
    sc = scope.site_clause()
    win = scope.window_days
    msg = await fetch_df(
        db, f"SELECT sent_at, direction, message_type, is_read, response_minutes FROM fact_message "
            f"WHERE sent_at >= :dwin {sc}", {**p, "dwin": today - dt.timedelta(days=win)})
    if msg.empty:
        return {"pc.messages": kpi(0, "Messages"), "pc.response": kpi(0, "Avg Response", unit="min"),
                "pc.read_rate": gauge(0, "Read Rate"), "pc.reports": kpi(0, "Daily Reports"),
                "pc.volume_trend": {"x": [], "series": [{"name": "Inbound", "data": []}, {"name": "Outbound", "data": []}]}}
    avg_resp = int(msg["response_minutes"].dropna().mean()) if msg["response_minutes"].notna().any() else 0
    read_rate = pct(safe_div(int(msg["is_read"].sum()), len(msg)) * 100)
    reports = int((msg["message_type"] == "report").sum())
    msg["d"] = pd.to_datetime(msg["sent_at"]).dt.date
    pivot = msg.groupby(["d", "direction"]).size().unstack(fill_value=0)
    pivot = pivot.sort_index().tail(30)
    vol = {"x": [d.strftime("%d %b") for d in pivot.index],
           "series": [{"name": "Inbound", "data": [int(v) for v in pivot.get("inbound", pd.Series([0]*len(pivot)))]},
                      {"name": "Outbound", "data": [int(v) for v in pivot.get("outbound", pd.Series([0]*len(pivot)))]}]}
    return {
        "pc.messages": kpi(int(len(msg)), "Messages", sub=f"last {win} days"),
        "pc.response": kpi(avg_resp, "Avg Response", unit="min", status="ok" if avg_resp < 60 else "warn"),
        "pc.read_rate": gauge(read_rate, "Read Rate"),
        "pc.reports": kpi(reports, "Daily Reports Sent", sub=f"last {win} days"),
        "pc.volume_trend": vol,
    }


# ─── Multi-site ───────────────────────────────────────────────────────────────
async def multisite(db: AsyncSession, scope: Scope) -> dict:
    sites = await fetch_df(db, "SELECT id, name, capacity, monthly_overhead FROM dim_site ORDER BY name", {})
    if sites.empty:
        return {"ms.ranking": {"columns": [], "rows": []}, "ms.occupancy": {"categories": [], "series": []},
                "ms.revenue": {"categories": [], "series": []}}
    month_start = dt.date.today().replace(day=1)
    occ_bar = {"categories": [], "series": [{"name": "Occupancy %", "data": []}]}
    rev_bar = {"categories": [], "series": [{"name": "Revenue £", "data": []}]}
    rows = []
    for _, s in sites.iterrows():
        filled = (await fetch_df(db, "SELECT COUNT(*) n FROM dim_child WHERE site_id=:s AND status='active'",
                                 {"s": int(s["id"])}))["n"].iloc[0]
        rev = (await fetch_df(db, "SELECT COALESCE(SUM(amount),0) r FROM fact_invoice WHERE site_id=:s AND period_month=:m",
                              {"s": int(s["id"]), "m": month_start}))["r"].iloc[0]
        inc = (await fetch_df(db, "SELECT COUNT(*) n FROM fact_incident WHERE site_id=:s AND status='open'",
                              {"s": int(s["id"])}))["n"].iloc[0]
        occ_p = round(float(filled) / s["capacity"] * 100, 1) if s["capacity"] else 0
        score = round(0.6 * occ_p + 0.4 * max(0, 100 - inc * 10), 1)
        occ_bar["categories"].append(s["name"]); occ_bar["series"][0]["data"].append(occ_p)
        rev_bar["categories"].append(s["name"]); rev_bar["series"][0]["data"].append(round(float(rev), 2))
        rows.append([s["name"], f"{occ_p}%", f"£{float(rev):,.0f}", int(inc), score])
    rows.sort(key=lambda r: r[4], reverse=True)
    ranking = {"columns": ["Site", "Occupancy", "Revenue (MTD)", "Open Incidents", "Score"], "rows": rows}
    return {"ms.ranking": ranking, "ms.occupancy": occ_bar, "ms.revenue": rev_bar}


# ─── Analytics & BI ───────────────────────────────────────────────────────────
async def analytics(db: AsyncSession, scope: Scope) -> dict:
    fin = await finance.compute(db, scope)
    occ = await occupancy.compute(db, scope)
    rev = fin["_rev_trend"]
    rev_growth = {"x": rev["x"], "series": [{"name": "Revenue £", "data": rev["series"][0]["data"]}]}
    # staff cost vs revenue ratio (proxy from monthly billed vs flat payroll estimate)
    cost_ratio = {"x": rev["x"], "series": [{"name": "Cost/Revenue %", "data": []}]}
    payroll_est = (await fetch_df(db, f"SELECT COALESCE(SUM(contract_hours*hourly_rate*4),0) c FROM dim_staff "
                                      f"WHERE 1=1 {scope.site_clause()}", scope.params))["c"].iloc[0]
    for v in rev["series"][0]["data"]:
        cost_ratio["series"][0]["data"].append(pct(safe_div(float(payroll_est), float(v)) * 100) if v else 0)
    funnel = occ["occ.waitlist_conv"]
    return {
        "bi.occ_trend": occ["occ.forecast"],
        "bi.rev_growth": rev_growth,
        "bi.cost_ratio": cost_ratio,
        "bi.funnel": funnel,
    }


# ─── Alerts ───────────────────────────────────────────────────────────────────
async def alerts(db: AsyncSession, scope: Scope) -> dict:
    comp = await compliance.compute(db, scope)
    stf = await staff.compute(db, scope)
    fin = await finance.compute(db, scope)
    att_today = dt.date.today()
    feed = []
    if comp["_high_open"]:
        feed.append(["High", "Compliance", f"{comp['_high_open']} high-severity incident(s) open"])
    if comp["_dbs_expired"]:
        feed.append(["High", "Staffing", f"{comp['_dbs_expired']} expired DBS check(s)"])
    if stf["_ratio_compliance"] < 100:
        feed.append(["High", "Ratio", f"{round(100 - stf['_ratio_compliance'])}% of rooms below ratio"])
    if fin["_arrears"] > 0:
        feed.append(["Medium", "Finance", f"£{fin['_arrears']:,.0f} outstanding"])
    unexplained = (await fetch_df(db, f"SELECT COUNT(*) n FROM fact_attendance WHERE date=:d AND status='unexplained' "
                                      f"{scope.site_clause()}", {**scope.params, "d": att_today}))["n"].iloc[0]
    if unexplained:
        feed.append(["Medium", "Attendance", f"{int(unexplained)} unexplained absence(s) today"])
    if not feed:
        feed.append(["Low", "All clear", "No active alerts"])
    sev_counts = pd.Series([f[0] for f in feed]).value_counts()
    pie = {"data": [{"name": s, "value": int(c)} for s, c in sev_counts.items()]}
    return {
        "alert.summary": kpi(len([f for f in feed if f[0] != "Low"]), "Active Alerts",
                             status="warn" if any(f[0] == "High" for f in feed) else "ok"),
        "alert.by_severity": pie,
        "alert.list": {"columns": ["Severity", "Area", "Detail"], "rows": feed},
    }


# ─── Operations ───────────────────────────────────────────────────────────────
async def operations(db: AsyncSession, scope: Scope) -> dict:
    today = dt.date.today()
    p = scope.params
    last = (await fetch_df(db, f"SELECT MAX(date) d FROM fact_attendance WHERE 1=1 {scope.site_clause()}", p))["d"].iloc[0]
    last = last or today
    present = (await fetch_df(db, f"SELECT COUNT(*) n FROM fact_attendance WHERE date=:d AND status='present' "
                                 f"{scope.site_clause()}", {**p, "d": last}))["n"].iloc[0]
    rota = await fetch_df(
        db, f"""SELECT st.first_name||' '||st.last_name AS staff, st.role_title, rm.name AS room,
                       sh.hours_scheduled, sh.absent
                FROM fact_staff_shift sh JOIN dim_staff st ON st.id=sh.staff_id
                LEFT JOIN dim_room rm ON rm.id=sh.room_id
                WHERE sh.date=:d {scope.site_clause('sh')} ORDER BY rm.name""", {**p, "d": last})
    rows = [[r["staff"], r["role_title"], r["room"] or "—",
             "Absent" if r["absent"] else f"{float(r['hours_scheduled']):.1f}h"]
            for _, r in rota.iterrows()] if not rota.empty else []
    on_duty = int((~rota["absent"]).sum()) if not rota.empty else 0
    return {
        "ops.today": kpi(int(present), "Present Today", sub=f"{on_duty} staff on duty"),
        "ops.rota": {"columns": ["Staff", "Role", "Room", "Shift"], "rows": rows},
    }


# ─── Mobile (parent-scoped) ───────────────────────────────────────────────────
async def mobile(db: AsyncSession, scope: Scope) -> dict:
    if not scope.child_id:
        return {"mob.child_status": kpi("—", "My Child Status", sub="No child linked"),
                "mob.updates": {"columns": ["When", "Type", "Detail"], "rows": []}}
    today = dt.date.today()
    att = await fetch_df(db, "SELECT date, status, check_in, check_out FROM fact_attendance "
                             "WHERE child_id=:c ORDER BY date DESC LIMIT 1", {"c": scope.child_id})
    status = att["status"].iloc[0].replace("_", " ").title() if not att.empty else "No record"
    meals = await fetch_df(db, "SELECT date, meal_type, intake_pct FROM fact_meal WHERE child_id=:c "
                               "ORDER BY date DESC, meal_type LIMIT 8", {"c": scope.child_id})
    rows = [[m["date"].strftime("%d %b"), m["meal_type"].capitalize(), f"{int(m['intake_pct'])}% eaten"]
            for _, m in meals.iterrows()] if not meals.empty else []
    return {
        "mob.child_status": kpi(status, "My Child Status", sub=f"as of {today.strftime('%d %b')}"),
        "mob.updates": {"columns": ["When", "Type", "Detail"], "rows": rows},
    }


# ─── AI / predictive ──────────────────────────────────────────────────────────
async def ai(db: AsyncSession, scope: Scope) -> dict:
    occ = await occupancy.compute(db, scope)
    fc = occ["occ.forecast"]
    # staffing shortfall projection: required staff vs scheduled (next 4 weeks, simple)
    shortfall = {"categories": ["Wk+1", "Wk+2", "Wk+3", "Wk+4"], "series": [{"name": "Projected gap (FTE)", "data": []}]}
    base = (await fetch_df(db, f"SELECT COUNT(*) n FROM dim_staff WHERE employment_status='active' {scope.site_clause()}",
                           scope.params))["n"].iloc[0]
    needed = (await fetch_df(db, f"SELECT COUNT(*) n FROM dim_child WHERE status='active' {scope.site_clause()}",
                             scope.params))["n"].iloc[0]
    req_staff = int(np.ceil(float(needed) / 5))
    rng = np.random.default_rng(7)
    for _ in range(4):
        shortfall["series"][0]["data"].append(int(max(0, req_staff - int(base) + rng.integers(-1, 3))))
    churn = await fetch_df(
        db, f"""SELECT c.first_name||' '||c.last_name AS child,
                       COALESCE(AVG(a.present::int)*100,0) AS attendance
                FROM dim_child c
                LEFT JOIN (SELECT child_id, (status='present') present FROM fact_attendance
                           WHERE date >= CURRENT_DATE - 30) a ON a.child_id=c.id
                WHERE c.status='active' {scope.site_clause('c')}
                GROUP BY c.id, child HAVING COALESCE(AVG(a.present::int)*100,0) < 80
                ORDER BY attendance LIMIT 10""", scope.params)
    rows = [[r["child"], f"{float(r['attendance']):.0f}% attendance", "Elevated"]
            for _, r in churn.iterrows()] if not churn.empty else []
    return {
        "ai.occ_predict": fc,
        "ai.staff_predict": shortfall,
        "ai.churn": {"columns": ["Family", "Signal", "Churn Risk"], "rows": rows},
    }
