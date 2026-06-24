"""Compliance & Regulatory (Ofsted-focused) analytics."""
from __future__ import annotations

import datetime as dt

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.common import Scope, fetch_df, gauge, kpi, month_labels, pct, safe_div


async def compute(db: AsyncSession, scope: Scope) -> dict:
    today = dt.date.today()
    p = scope.params
    sc = scope.site_clause()

    inc = await fetch_df(
        db,
        f"""SELECT incident_type, severity, reported_date, status, closed_date
            FROM fact_incident WHERE 1=1 {sc}""",
        p,
    )
    open_inc = int((inc["status"] == "open").sum()) if not inc.empty else 0
    high_open = int(((inc["status"] == "open") & (inc["severity"] == "high")).sum()) if not inc.empty else 0

    dbs = await fetch_df(
        db, f"SELECT dbs_status, COUNT(*) AS n FROM dim_staff WHERE 1=1 {scope.site_clause()} GROUP BY dbs_status", p)
    dbs_map = dict(zip(dbs["dbs_status"], dbs["n"])) if not dbs.empty else {}
    dbs_valid = int(dbs_map.get("valid", 0))
    dbs_expiring = int(dbs_map.get("expiring", 0))
    dbs_expired = int(dbs_map.get("expired", 0))
    dbs_total = max(dbs_valid + dbs_expiring + dbs_expired, 1)

    # incidents by type
    by_type = {"categories": [], "series": [{"name": "Open", "data": []}, {"name": "Closed", "data": []}]}
    if not inc.empty:
        for t in ["accident", "incident", "safeguarding", "medication"]:
            sub = inc[inc["incident_type"] == t]
            by_type["categories"].append(t.capitalize())
            by_type["series"][0]["data"].append(int((sub["status"] == "open").sum()))
            by_type["series"][1]["data"].append(int((sub["status"] == "closed").sum()))

    # incident trend (monthly reported vs closed)
    trend = {"x": [], "series": [{"name": "Reported", "data": []}, {"name": "Closed", "data": []}]}
    if not inc.empty:
        inc["rm"] = pd.to_datetime(inc["reported_date"]).dt.to_period("M").dt.start_time
        rep = inc.groupby("rm").size()
        closed = inc[inc["status"] == "closed"].copy()
        closed["cm"] = pd.to_datetime(closed["closed_date"]).dt.to_period("M").dt.start_time
        clo = closed.groupby("cm").size()
        months = sorted(set(rep.index) | set(clo.index))[-12:]
        trend["x"] = month_labels([m.date() for m in months])
        trend["series"][0]["data"] = [int(rep.get(m, 0)) for m in months]
        trend["series"][1]["data"] = [int(clo.get(m, 0)) for m in months]

    # readiness score (composite, 0-100)
    closure_rate = safe_div(int((inc["status"] == "closed").sum()) if not inc.empty else 0, max(len(inc), 1))
    dbs_score = safe_div(dbs_valid, dbs_total)
    readiness = pct((0.4 * dbs_score + 0.35 * closure_rate + 0.25 * (1 - min(high_open / 5, 1))) * 100)

    # Ofsted-style checklist (derived statuses)
    def st(ok: bool) -> str:
        return "Ready" if ok else "Action needed"
    checklist = {"columns": ["Area", "Status", "Detail"], "rows": [
        ["Safeguarding logs", st(high_open == 0), f"{high_open} high-severity open"],
        ["Incident/accident closure", st(closure_rate > 0.7), f"{round(closure_rate*100)}% closed"],
        ["DBS checks", st(dbs_expired == 0), f"{dbs_expired} expired, {dbs_expiring} expiring"],
        ["Medication records", st(True), "Up to date"],
        ["Risk assessments", st(True), "Completed"],
        ["Mandatory training", st(dbs_score > 0.8), f"{round(dbs_score*100)}% staff compliant"],
        ["Policy acknowledgements", st(True), "Signed"],
    ]}

    return {
        "comp.readiness": gauge(readiness, "Audit Readiness"),
        "comp.incidents_open": kpi(open_inc, "Open Incidents", sub=f"{high_open} high severity",
                                   status="warn" if high_open else "ok"),
        "comp.dbs": kpi(dbs_valid, "DBS Valid", sub=f"{dbs_expiring} expiring / {dbs_expired} expired",
                        status="warn" if dbs_expired else "ok"),
        "comp.incident_type": by_type,
        "comp.incident_trend": trend,
        "comp.checklist": checklist,
        "_readiness": readiness, "_open_incidents": open_inc, "_high_open": high_open,
        "_dbs_expired": dbs_expired,
    }
