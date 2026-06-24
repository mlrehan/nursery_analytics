"""Attendance & Check-in analytics."""
from __future__ import annotations

import datetime as dt

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.common import Scope, fetch_df, gauge, kpi, pct, safe_div


async def compute(db: AsyncSession, scope: Scope) -> dict:
    today = dt.date.today()
    p = scope.params
    sc = scope.site_clause()
    child_clause = " AND child_id = :scope_child " if scope.child_id else " "

    att = await fetch_df(
        db,
        f"""SELECT a.date, a.status, a.late_pickup, a.room_id, r.name AS room_name, r.room_type
            FROM fact_attendance a LEFT JOIN dim_room r ON r.id = a.room_id
            WHERE a.date >= :d60 {scope.site_clause('a')} {child_clause.replace('child_id','a.child_id')}""",
        {**p, "d60": today - dt.timedelta(days=60)},
    )
    if att.empty:
        return _empty()

    last_day = att["date"].max()
    today_rows = att[att["date"] == last_day]
    present_today = int((today_rows["status"] == "present").sum())
    absent_today = int((today_rows["status"] != "present").sum())

    att30 = att[att["date"] >= (today - dt.timedelta(days=30))]
    rate = pct(safe_div(int((att30["status"] == "present").sum()), len(att30)) * 100)
    late = int(att30["late_pickup"].sum())

    # daily trend
    daily = att.groupby("date").apply(
        lambda d: safe_div((d["status"] == "present").sum(), len(d)) * 100, include_groups=False)
    daily = daily.sort_index().tail(30)
    trend = {"x": [d.strftime("%d %b") for d in daily.index],
             "series": [{"name": "Attendance %", "data": [round(float(v), 1) for v in daily.values]}]}

    # absence reasons pie
    absences = att30[att30["status"] != "present"]
    reason_map = {"absent_illness": "Illness", "absent_holiday": "Holiday", "unexplained": "Unexplained"}
    rc = absences["status"].value_counts()
    pie = {"data": [{"name": reason_map.get(s, s), "value": int(c)} for s, c in rc.items()]}

    # heatmap: day-of-week x room (attendance %)
    heat = {"x": [], "y": [], "data": [], "max": 100}
    if not att30.empty and att30["room_name"].notna().any():
        att30 = att30.copy()
        att30["dow"] = pd.to_datetime(att30["date"]).dt.dayofweek
        dow_names = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        rooms = [r for r in att30["room_name"].dropna().unique()]
        heat["x"] = dow_names
        heat["y"] = rooms
        for yi, room in enumerate(rooms):
            for xi, dow in enumerate(range(5)):
                sub = att30[(att30["room_name"] == room) & (att30["dow"] == dow)]
                val = round(safe_div((sub["status"] == "present").sum(), len(sub)) * 100, 0) if len(sub) else 0
                heat["data"].append([xi, yi, int(val)])

    return {
        "att.present": kpi(present_today, "Present Today"),
        "att.rate": gauge(rate, "Attendance Rate"),
        "att.absent": kpi(absent_today, "Absent Today", status="warn" if absent_today else "ok"),
        "att.late": kpi(late, "Late Pickups", sub="last 30 days"),
        "att.trend": trend,
        "att.absence_mix": pie,
        "att.heatmap": heat,
        "_present_today": present_today, "_rate": rate,
    }


def _empty() -> dict:
    return {
        "att.present": kpi(0, "Present Today"), "att.rate": gauge(0, "Attendance Rate"),
        "att.absent": kpi(0, "Absent Today"), "att.late": kpi(0, "Late Pickups"),
        "att.trend": {"x": [], "series": [{"name": "Attendance %", "data": []}]},
        "att.absence_mix": {"data": []}, "att.heatmap": {"x": [], "y": [], "data": [], "max": 100},
        "_present_today": 0, "_rate": 0,
    }
