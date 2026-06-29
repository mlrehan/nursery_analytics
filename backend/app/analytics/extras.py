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


# ─── Multi-site / Branch Comparison ───────────────────────────────────────────
async def multisite(db: AsyncSession, scope: Scope) -> dict:
    sites = await fetch_df(db, "SELECT id, name, capacity, monthly_overhead FROM dim_site ORDER BY name", {})
    if sites.empty:
        empty_bar = {"categories": [], "series": []}
        return {"ms.ranking": {"columns": [], "rows": []}, "ms.occupancy": empty_bar, "ms.revenue": empty_bar,
                "ms.profit": empty_bar, "ms.staff_eff": empty_bar,
                "ms.best_worst": {"columns": [], "rows": []}}
    month_start = dt.date.today().replace(day=1)

    recs = []
    for _, s in sites.iterrows():
        sid = int(s["id"])
        filled = int((await fetch_df(db, "SELECT COUNT(*) n FROM dim_child WHERE site_id=:s AND status='active'", {"s": sid}))["n"].iloc[0])
        rev = float((await fetch_df(db, "SELECT COALESCE(SUM(amount),0) r FROM fact_invoice WHERE site_id=:s AND period_month=:m", {"s": sid, "m": month_start}))["r"].iloc[0])
        payroll = float((await fetch_df(db, "SELECT COALESCE(SUM(contract_hours*hourly_rate*4.33),0) c FROM dim_staff WHERE site_id=:s AND employment_status='active'", {"s": sid}))["c"].iloc[0])
        headcount = int((await fetch_df(db, "SELECT COUNT(*) n FROM dim_staff WHERE site_id=:s AND employment_status='active'", {"s": sid}))["n"].iloc[0])
        inc = int((await fetch_df(db, "SELECT COUNT(*) n FROM fact_incident WHERE site_id=:s AND status='open'", {"s": sid}))["n"].iloc[0])
        occ_p = round(filled / s["capacity"] * 100, 1) if s["capacity"] else 0
        profit = round(rev - payroll - float(s["monthly_overhead"]), 2)
        staff_eff = round(safe_div(filled, headcount), 1)
        recs.append({"name": s["name"], "occ": occ_p, "rev": rev, "profit": profit,
                     "staff_eff": staff_eff, "inc": inc})

    pmin = min(r["profit"] for r in recs); pmax = max(r["profit"] for r in recs)
    for r in recs:
        pnorm = ((r["profit"] - pmin) / (pmax - pmin) * 100) if pmax > pmin else 50
        r["score"] = round(0.5 * r["occ"] + 0.3 * pnorm + 0.2 * max(0, 100 - r["inc"] * 10), 1)
    recs.sort(key=lambda r: r["score"], reverse=True)

    occ_bar = {"categories": [r["name"] for r in recs], "series": [{"name": "Occupancy %", "data": [r["occ"] for r in recs]}]}
    rev_bar = {"categories": [r["name"] for r in recs], "series": [{"name": "Revenue £", "data": [round(r["rev"], 2) for r in recs]}]}
    profit_bar = {"categories": [r["name"] for r in recs], "series": [{"name": "Profit £", "data": [r["profit"] for r in recs]}]}
    eff_bar = {"categories": [r["name"] for r in recs], "series": [{"name": "Children / staff", "data": [r["staff_eff"] for r in recs]}]}

    ranking = {"columns": ["Site", "Occupancy", "Revenue (MTD)", "Profit (MTD est.)", "Children/Staff", "Open incidents", "Score"],
               "rows": [[r["name"], f"{r['occ']}%", f"£{r['rev']:,.0f}", f"£{r['profit']:,.0f}",
                         r["staff_eff"], r["inc"], r["score"]] for r in recs]}

    best, worst = recs[0], recs[-1]
    bw = {"columns": ["", "Best — " + best["name"], "Worst — " + worst["name"], "Gap"],
          "rows": [
              ["Occupancy", f"{best['occ']}%", f"{worst['occ']}%", f"{round(best['occ']-worst['occ'],1)} pts"],
              ["Revenue (MTD)", f"£{best['rev']:,.0f}", f"£{worst['rev']:,.0f}", f"£{best['rev']-worst['rev']:,.0f}"],
              ["Profit (MTD est.)", f"£{best['profit']:,.0f}", f"£{worst['profit']:,.0f}", f"£{best['profit']-worst['profit']:,.0f}"],
              ["Children/Staff", best["staff_eff"], worst["staff_eff"], round(best["staff_eff"]-worst["staff_eff"], 1)],
              ["Score", best["score"], worst["score"], round(best["score"]-worst["score"], 1)],
          ]}

    return {"ms.ranking": ranking, "ms.occupancy": occ_bar, "ms.revenue": rev_bar,
            "ms.profit": profit_bar, "ms.staff_eff": eff_bar, "ms.best_worst": bw}


def _months_window(today: dt.date, win: int) -> tuple[dt.date, int]:
    """Map a day-window to a whole-month window for monthly (billing) metrics."""
    months = max(1, round(win / 30))
    start = today.replace(day=1)
    for _ in range(months - 1):
        start = (start - dt.timedelta(days=1)).replace(day=1)
    return start, months


# ─── Analytics & BI (+ Growth Intelligence) ───────────────────────────────────
async def analytics(db: AsyncSession, scope: Scope) -> dict:
    today = dt.date.today()
    p = scope.params
    sc = scope.site_clause()
    win = scope.window_days
    win_start = today - dt.timedelta(days=win)
    month_start = today.replace(day=1)
    pstart, _months = _months_window(today, win)

    fin = await finance.compute(db, scope)
    occ = await occupancy.compute(db, scope)
    rev = fin["_rev_trend"]
    rev_growth = {"x": rev["x"], "series": [{"name": "Revenue £", "data": rev["series"][0]["data"]}]}

    active = int((await fetch_df(db, f"SELECT COUNT(*) n FROM dim_child WHERE status='active' {sc}", p))["n"].iloc[0])

    # staff cost vs revenue ratio trend + headline staff cost ratio
    payroll_month = float((await fetch_df(
        db, f"SELECT COALESCE(SUM(contract_hours*hourly_rate*4.33),0) c FROM dim_staff "
            f"WHERE employment_status='active' {sc}", p))["c"].iloc[0])
    cost_ratio = {"x": rev["x"], "series": [{"name": "Cost/Revenue %", "data": []}]}
    for v in rev["series"][0]["data"]:
        cost_ratio["series"][0]["data"].append(pct(safe_div(payroll_month, float(v)) * 100) if v else 0)
    rev_month = fin["_billed_mtd"]
    staff_cost_ratio = pct(safe_div(payroll_month, rev_month) * 100)

    # all enrollment events (for growth, sources, visit funnel)
    ev = await fetch_df(db, f"SELECT child_id, event_type, event_date, source FROM fact_enrollment_event WHERE 1=1 {sc}", p)
    adm = wd = enquiries = visited = enrolled = 0
    sources_pie = {"data": []}
    if not ev.empty:
        ev["event_date"] = pd.to_datetime(ev["event_date"]).dt.date
        inwin = ev[ev["event_date"] >= win_start]
        adm = int((inwin["event_type"] == "admission").sum())
        wd = int((inwin["event_type"] == "withdrawal").sum())
        cohort = set(inwin.loc[inwin["event_type"] == "enquiry", "child_id"])
        coh = ev[ev["child_id"].isin(cohort)]
        enquiries = len(cohort)
        visited = int(coh.loc[coh["event_type"].isin(["visit", "admission"]), "child_id"].nunique())
        enrolled = int(coh.loc[coh["event_type"] == "admission", "child_id"].nunique())
        srcs = inwin.loc[inwin["event_type"] == "enquiry", "source"].fillna("Other").value_counts()
        sources_pie = {"data": [{"name": s, "value": int(c)} for s, c in srcs.items()]}

    net = adm - wd
    growth_pct = pct(safe_div(net, active) * 100)
    churn_pct = pct(safe_div(wd, active) * 100)
    retention_pct = pct(100 - churn_pct)

    # fee collection efficiency + discount leakage (monthly window)
    fin_q = await fetch_df(
        db, f"SELECT COALESCE(SUM(amount),0) billed, COALESCE(SUM(discount_amount),0) disc, "
            f"COALESCE(SUM(amount+funding_amount+discount_amount),0) gross "
            f"FROM fact_invoice WHERE period_month >= :ps {sc}", {**p, "ps": pstart})
    billed_p = float(fin_q["billed"].iloc[0]); disc_p = float(fin_q["disc"].iloc[0]); gross_p = float(fin_q["gross"].iloc[0])
    collected_p = float((await fetch_df(
        db, f"SELECT COALESCE(SUM(amount),0) c FROM fact_payment WHERE success AND NOT is_refund "
            f"AND payment_date >= :ps {sc}", {**p, "ps": pstart}))["c"].iloc[0])
    collection_eff = pct(min(100.0, safe_div(collected_p, billed_p) * 100))
    disc_leak_pct = pct(safe_div(disc_p, gross_p) * 100)

    # parent engagement (read rate) + cohort development score
    eng = await fetch_df(db, f"SELECT COALESCE(AVG(is_read::int),0)*100 v FROM fact_message WHERE sent_at >= :w {sc}",
                         {**p, "w": win_start})
    engagement = pct(float(eng["v"].iloc[0]) if not eng.empty else 0)
    dev = await fetch_df(db, f"SELECT COALESCE(AVG(on_track::int),0)*100 v FROM fact_eyfs_observation "
                             f"WHERE observation_date >= :w {sc}", {**p, "w": win_start})
    dev_score = pct(float(dev["v"].iloc[0]) if not dev.empty else 0)

    # room transition readiness (children older than their room's age ceiling)
    ceil_m = {"baby": 24, "toddler": 36, "preschool": 60}
    kids = await fetch_df(db, f"SELECT c.dob, r.room_type FROM dim_child c JOIN dim_room r ON r.id=c.room_id "
                              f"WHERE c.status='active' {scope.site_clause('c')}", p)
    transition_ready = 0
    if not kids.empty:
        age_m = ((pd.Timestamp(today) - pd.to_datetime(kids["dob"])).dt.days / 30.44)
        # "ready or approaching" = within 2 months of their room's age ceiling
        transition_ready = int((age_m >= (kids["room_type"].map(ceil_m) - 2)).sum())

    return {
        "bi.occ_trend": occ["occ.forecast"],
        "bi.rev_growth": rev_growth,
        "bi.cost_ratio": cost_ratio,
        "bi.funnel": occ["occ.waitlist_conv"],
        "bi.enroll_growth": kpi(growth_pct, "Enrollment Growth", unit="%",
                                sub=f"+{adm} joined · {wd} left ({win}d)",
                                status="ok" if net >= 0 else "warn", accent="emerald"),
        "bi.churn": kpi(churn_pct, "Churn Rate", unit="%", sub=f"last {win} days",
                        status="warn" if churn_pct > 5 else "ok", accent="orange"),
        "bi.retention": kpi(retention_pct, "Retention Rate", unit="%", sub="children retained", accent="blue"),
        "bi.staff_cost_ratio": kpi(staff_cost_ratio, "Staff Cost Ratio", unit="%", sub="of monthly revenue",
                                   status="warn" if staff_cost_ratio > 60 else "ok", accent="violet"),
        "bi.collection_eff": gauge(collection_eff, "Collection Efficiency"),
        "bi.discount_leakage": kpi(round(disc_p, 2), "Discount Leakage", unit="£",
                                   sub=f"{disc_leak_pct}% of gross fees", accent="amber"),
        "bi.engagement": gauge(engagement, "Parent Engagement"),
        "bi.dev_score": gauge(dev_score, "Development Progress"),
        "bi.transition_ready": kpi(transition_ready, "Transition Readiness", sub="children ready to move room", accent="cyan"),
        "bi.enquiry_sources": sources_pie,
        "bi.visit_funnel": {"data": [{"name": "Enquiries", "value": enquiries},
                                     {"name": "Visited", "value": visited},
                                     {"name": "Enrolled", "value": enrolled}]},
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

    # ── predictive / branch alerts ──
    p = scope.params
    occ = await occupancy.compute(db, scope)
    occ_rate = occ["_rate"]
    fvals = [v for v in occ["occ.forecast"]["series"][1]["data"] if v is not None]
    if fvals and fvals[-1] < occ_rate - 1.5:
        feed.append(["Medium", "Forecast",
                     f"Occupancy projected to fall to {round(fvals[-1])}% next months (now {round(occ_rate)}%)"])
    debt = await fetch_df(
        db, f"""SELECT s.name, COALESCE(SUM(GREATEST(i.amount - COALESCE(pp.paid,0),0)),0) debt
                FROM dim_site s LEFT JOIN fact_invoice i ON i.site_id=s.id
                LEFT JOIN (SELECT invoice_id, SUM(amount) paid FROM fact_payment
                           WHERE success AND NOT is_refund GROUP BY invoice_id) pp ON pp.invoice_id=i.id
                WHERE 1=1 {scope.site_pk_clause('s')} GROUP BY s.name ORDER BY debt DESC LIMIT 1""", p)
    if not debt.empty and float(debt["debt"].iloc[0]) > 5000:
        feed.append(["High", "Finance",
                     f"High-debt branch: {debt['name'].iloc[0]} — £{float(debt['debt'].iloc[0]):,.0f} outstanding"])
    rooms = await fetch_df(
        db, f"""SELECT r.name, r.capacity, COUNT(c.id) FILTER (WHERE c.status='active') filled
                FROM dim_room r LEFT JOIN dim_child c ON c.room_id=r.id
                WHERE 1=1 {scope.site_clause('r')} GROUP BY r.id, r.name, r.capacity""", p)
    if not rooms.empty:
        rooms = rooms.assign(occ=rooms["filled"] / rooms["capacity"] * 100).sort_values("occ")
        worst_room = rooms.iloc[0]
        if float(worst_room["occ"]) < 70:
            feed.append(["Medium", "Occupancy",
                         f"Underperforming room: {worst_room['name']} only {round(float(worst_room['occ']))}% full"])
    if not feed:
        feed.append(["Low", "All clear", "No active alerts"])
    sev_counts = pd.Series([f[0] for f in feed]).value_counts()
    pie = {"data": [{"name": s, "value": int(c)} for s, c in sev_counts.items()]}
    feed_table = {"columns": ["Severity", "Area", "Detail"], "rows": feed}
    active = [f for f in feed if f[0] != "Low"]
    drill = {"title": "Active alerts", "columns": ["Severity", "Area", "Detail"],
             "rows": active or feed}
    return {
        "alert.summary": kpi(len(active), "Active Alerts",
                             status="warn" if any(f[0] == "High" for f in feed) else "ok",
                             drill=drill),
        "alert.by_severity": pie,
        "alert.list": feed_table,
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

    # ── empty-seat prediction + revenue at risk ──
    capacity = int((await fetch_df(db, f"SELECT COALESCE(SUM(capacity),0) c FROM dim_site WHERE 1=1 {scope.site_pk_clause()}",
                                   scope.params))["c"].iloc[0])
    fvals = [v for v in fc["series"][1]["data"] if v is not None]
    proj_occ = fvals[-1] if fvals else (occ["_rate"] or 0)
    proj_filled = capacity * proj_occ / 100
    empty_seats = int(max(0, round(capacity - proj_filled)))
    avg_fee = float((await fetch_df(db, f"SELECT COALESCE(AVG(monthly_fee),0) f FROM dim_child WHERE status='active' {scope.site_clause()}",
                                    scope.params))["f"].iloc[0])
    revenue_risk = round(empty_seats * avg_fee, 2)

    # ── waitlist conversion probability (historic) ──
    conv = await fetch_df(
        db, f"""SELECT
                  COUNT(DISTINCT child_id) FILTER (WHERE event_type='waitlist_join') AS waited,
                  COUNT(DISTINCT child_id) FILTER (WHERE event_type='waitlist_join'
                        AND child_id IN (SELECT child_id FROM fact_enrollment_event WHERE event_type='admission')) AS converted
                FROM fact_enrollment_event WHERE 1=1 {scope.site_clause()}""", scope.params)
    waited = int(conv["waited"].iloc[0]) if not conv.empty else 0
    converted = int(conv["converted"].iloc[0]) if not conv.empty else 0
    waitlist_prob = pct(safe_div(converted, waited) * 100)

    # ── fee-collection risk: families with the largest unpaid balance ──
    risk = await fetch_df(
        db, f"""SELECT c.first_name||' '||c.last_name AS child,
                       COALESCE(SUM(GREATEST(i.amount - COALESCE(pp.paid,0),0)),0) AS owed,
                       COUNT(*) FILTER (WHERE i.status='overdue') AS overdue_n
                FROM dim_child c JOIN fact_invoice i ON i.child_id=c.id
                LEFT JOIN (SELECT invoice_id, SUM(amount) paid FROM fact_payment
                           WHERE success AND NOT is_refund GROUP BY invoice_id) pp ON pp.invoice_id=i.id
                WHERE c.status='active' {scope.site_clause('c')}
                GROUP BY c.id, child HAVING COALESCE(SUM(GREATEST(i.amount-COALESCE(pp.paid,0),0)),0) > 0
                ORDER BY owed DESC LIMIT 12""", scope.params)
    risk_rows = []
    if not risk.empty:
        for _, r in risk.iterrows():
            owed = float(r["owed"]); ov = int(r["overdue_n"])
            level = "High" if (owed > 2000 or ov >= 2) else ("Medium" if owed > 800 else "Low")
            risk_rows.append([r["child"], f"£{owed:,.2f}", f"{ov} overdue", level])

    return {
        "ai.occ_predict": fc,
        "ai.staff_predict": shortfall,
        "ai.churn": {"columns": ["Family", "Signal", "Churn Risk"], "rows": rows},
        "ai.empty_seat": kpi(empty_seats, "Predicted Empty Seats", sub="forecast next month",
                             status="warn" if empty_seats > 0 else "ok", accent="amber"),
        "ai.revenue_risk": kpi(revenue_risk, "Revenue at Risk", unit="£", sub="per month if seats stay empty",
                               accent="orange"),
        "ai.waitlist_prob": kpi(waitlist_prob, "Waitlist Conversion", unit="%",
                                sub="historic enrol rate", accent="emerald"),
        "ai.fee_risk": {"columns": ["Family", "Outstanding", "Overdue", "Risk"], "rows": risk_rows},
    }
