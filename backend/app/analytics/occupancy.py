"""Enrollment & Occupancy analytics."""
from __future__ import annotations

import datetime as dt

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.common import Scope, fetch_df, gauge, kpi, linear_forecast, month_labels, pct, safe_div


async def compute(db: AsyncSession, scope: Scope) -> dict:
    today = dt.date.today()
    p = scope.params
    sc = scope.site_clause()

    cap_df = await fetch_df(db, f"SELECT COALESCE(SUM(capacity),0) AS cap FROM dim_site WHERE 1=1 {scope.site_pk_clause()}", p)
    capacity = int(cap_df["cap"].iloc[0])

    children = await fetch_df(
        db,
        f"""SELECT c.id, c.status, c.dob, c.funding_type, r.room_type
            FROM dim_child c LEFT JOIN dim_room r ON r.id = c.room_id
            WHERE 1=1 {scope.site_clause('c')}""",
        p,
    )
    active = children[children["status"] == "active"] if not children.empty else children
    filled = len(active)
    waitlist = int((children["status"] == "waitlist").sum()) if not children.empty else 0
    rate = pct(safe_div(filled, capacity) * 100)

    # all enrollment events (scoped) — used for admissions/withdrawals and the funnel
    win = scope.window_days
    win_lbl = f"last {win} days"
    win_start = today - dt.timedelta(days=win)
    all_ev = await fetch_df(
        db, f"SELECT child_id, event_type, event_date FROM fact_enrollment_event WHERE 1=1 {sc}", p)
    if not all_ev.empty:
        all_ev["event_date"] = pd.to_datetime(all_ev["event_date"]).dt.date
        in_win = all_ev[all_ev["event_date"] >= win_start]
        adm = int((in_win["event_type"] == "admission").sum())
        wd = int((in_win["event_type"] == "withdrawal").sum())
    else:
        in_win = all_ev
        adm = wd = 0

    # by room type
    by_room_payload = {"categories": [], "series": [{"name": "Filled", "data": []},
                                                    {"name": "Capacity", "data": []}]}
    if not active.empty:
        room_cap = await fetch_df(
            db, f"SELECT room_type, SUM(capacity) AS cap FROM dim_room WHERE 1=1 {scope.site_clause()} GROUP BY room_type", p)
        filled_by = active.groupby("room_type").size()
        order = ["baby", "toddler", "preschool"]
        cap_map = dict(zip(room_cap["room_type"], room_cap["cap"])) if not room_cap.empty else {}
        for rt in order:
            by_room_payload["categories"].append(rt.capitalize())
            by_room_payload["series"][0]["data"].append(int(filled_by.get(rt, 0)))
            by_room_payload["series"][1]["data"].append(int(cap_map.get(rt, 0)))

    # age distribution
    age_payload = {"categories": ["0-2y", "2-3y", "3-4y", "4-5y"], "series": [{"name": "Children", "data": [0, 0, 0, 0]}]}
    if not active.empty:
        ages = ((pd.Timestamp(today) - pd.to_datetime(active["dob"])).dt.days / 365.25)
        bins = [0, 2, 3, 4, 99]
        cats = pd.cut(ages, bins=bins, right=False, labels=["0-2y", "2-3y", "3-4y", "4-5y"])
        counts = cats.value_counts()
        age_payload["series"][0]["data"] = [int(counts.get(lbl, 0)) for lbl in age_payload["categories"]]

    # waitlist conversion funnel — a true COHORT: take everyone who ENQUIRED in the
    # window, then count how far that same group progressed. Each stage is a subset of
    # the previous, so it is always monotonic (Enquiries ≥ Waitlisted ≥ Enrolled).
    enquiries = waitlisted = enrolled = 0
    if not all_ev.empty:
        cohort = set(in_win.loc[in_win["event_type"] == "enquiry", "child_id"])
        coh = all_ev[all_ev["child_id"].isin(cohort)]
        enquiries = len(cohort)
        # reached a waitlist place OR went straight to enrolment
        waitlisted = int(coh.loc[coh["event_type"].isin(["waitlist_join", "admission"]), "child_id"].nunique())
        enrolled = int(coh.loc[coh["event_type"] == "admission", "child_id"].nunique())
    funnel = {"data": [{"name": "Enquiries", "value": enquiries},
                       {"name": "Waitlisted / Offered", "value": waitlisted},
                       {"name": "Enrolled", "value": enrolled}]}

    # occupancy forecast: net enrolled by month from cumulative events + linear forecast
    hist = await fetch_df(
        db,
        f"""SELECT date_trunc('month', event_date)::date AS m,
                   SUM(CASE WHEN event_type='admission' THEN 1
                            WHEN event_type='withdrawal' THEN -1 ELSE 0 END) AS net
            FROM fact_enrollment_event WHERE 1=1 {sc} GROUP BY 1 ORDER BY 1""",
        p,
    )
    forecast_payload = {"x": [], "series": [{"name": "Occupancy %", "data": []},
                                            {"name": "Forecast", "data": []}]}
    if not hist.empty:
        hist["cum"] = hist["net"].cumsum()
        hist["occ"] = (hist["cum"] / capacity * 100).clip(lower=0) if capacity else 0
        recent = hist.tail(9)
        occ_vals = [round(float(v), 1) for v in recent["occ"]]
        fc = linear_forecast(occ_vals, 6)
        labels = month_labels(list(recent["m"]))
        future_labels = month_labels([_add_months(today.replace(day=1), i + 1) for i in range(6)])
        forecast_payload["x"] = labels + future_labels
        forecast_payload["series"][0]["data"] = occ_vals + [None] * 6
        forecast_payload["series"][1]["data"] = [None] * (len(occ_vals) - 1) + [occ_vals[-1]] + [round(v, 1) for v in fc]

    # funding mix (UK free-hours): private / 15h / 30h
    funding_labels = {"private": "Private", "funded_15": "15h funded", "funded_30": "30h funded"}
    funding_payload = {"data": []}
    if not active.empty and "funding_type" in active:
        fc = active["funding_type"].fillna("private").value_counts()
        funding_payload = {"data": [{"name": funding_labels.get(k, k), "value": int(v)} for k, v in fc.items()]}

    return {
        "occ.capacity": kpi(filled, "Filled vs Capacity", sub=f"of {capacity} places · as of today"),
        "occ.rate": gauge(rate, "Occupancy"),
        "occ.funding": funding_payload,
        "occ.admissions": kpi(adm, "New Admissions", sub=win_lbl),
        "occ.withdrawals": kpi(wd, "Withdrawals", sub=win_lbl),
        "occ.by_room": by_room_payload,
        "occ.age_dist": age_payload,
        "occ.waitlist_conv": funnel,
        "occ.forecast": forecast_payload,
        # values reused by executive
        "_capacity": capacity, "_filled": filled, "_rate": rate, "_waitlist": waitlist,
    }


def _add_months(d: dt.date, n: int) -> dt.date:
    m = d.month - 1 + n
    return dt.date(d.year + m // 12, m % 12 + 1, 1)
