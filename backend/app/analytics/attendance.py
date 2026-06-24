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

    win = scope.window_days
    win_lbl = f"last {win} days"
    att = await fetch_df(
        db,
        f"""SELECT a.date, a.status, a.late_pickup, a.check_in, a.check_out, a.room_id,
                   r.name AS room_name, r.room_type
            FROM fact_attendance a LEFT JOIN dim_room r ON r.id = a.room_id
            WHERE a.date >= :dwin {scope.site_clause('a')} {child_clause.replace('child_id','a.child_id')}""",
        {**p, "dwin": today - dt.timedelta(days=win)},
    )
    if att.empty:
        return _empty()

    last_day = att["date"].max()
    today_rows = att[att["date"] == last_day]
    present_today = int((today_rows["status"] == "present").sum())
    absent_today = int((today_rows["status"] != "present").sum())

    attw = att  # already restricted to the active window
    rate = pct(safe_div(int((attw["status"] == "present").sum()), len(attw)) * 100)
    late = int(attw["late_pickup"].sum())

    # daily trend (cap points for readability on long windows)
    daily = att.groupby("date").apply(
        lambda d: safe_div((d["status"] == "present").sum(), len(d)) * 100, include_groups=False)
    daily = daily.sort_index().tail(min(win, 120))
    trend = {"x": [d.strftime("%d %b") for d in daily.index],
             "series": [{"name": "Attendance %", "data": [round(float(v), 1) for v in daily.values]}]}
    spark = [round(float(v), 1) for v in daily.tail(14).values]

    # absence reasons pie
    absences = attw[attw["status"] != "present"]
    reason_map = {"absent_illness": "Illness", "absent_holiday": "Holiday", "unexplained": "Unexplained"}
    rc = absences["status"].value_counts()
    pie = {"data": [{"name": reason_map.get(s, s), "value": int(c)} for s, c in rc.items()]}

    # heatmap: day-of-week x room (attendance %)
    heat = {"x": [], "y": [], "data": [], "max": 100}
    if not attw.empty and attw["room_name"].notna().any():
        hw = attw.copy()
        hw["dow"] = pd.to_datetime(hw["date"]).dt.dayofweek
        dow_names = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        rooms = [r for r in hw["room_name"].dropna().unique()]
        heat["x"] = dow_names
        heat["y"] = rooms
        for yi, room in enumerate(rooms):
            for xi, dow in enumerate(range(5)):
                sub = hw[(hw["room_name"] == room) & (hw["dow"] == dow)]
                val = round(safe_div((sub["status"] == "present").sum(), len(sub)) * 100, 0) if len(sub) else 0
                heat["data"].append([xi, yi, int(val)])

    # utilisation by session: average AM vs PM headcount (spot afternoon gaps)
    present = attw[attw["status"] == "present"].copy()
    time_of_day = {"categories": ["Morning (AM)", "Afternoon (PM)"], "series": [{"name": "Avg children present", "data": [0, 0]}]}
    if not present.empty:
        n_days = present["date"].nunique() or 1
        ci = pd.to_datetime(present["check_in"])
        co = pd.to_datetime(present["check_out"])
        am = int((ci.dt.hour < 13).sum())
        pm = int((co.dt.hour >= 14).sum())
        time_of_day["series"][0]["data"] = [round(am / n_days, 1), round(pm / n_days, 1)]

    return {
        "att.present": kpi(present_today, "Present Today", accent="cyan", spark=spark),
        "att.time_of_day": time_of_day,
        "att.rate": gauge(rate, "Attendance Rate"),
        "att.absent": kpi(absent_today, "Absent Today", status="warn" if absent_today else "ok", accent="amber"),
        "att.late": kpi(late, "Late Pickups", sub=win_lbl, accent="violet"),
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
        "att.time_of_day": {"categories": ["Morning (AM)", "Afternoon (PM)"], "series": [{"name": "Avg children present", "data": [0, 0]}]},
        "_present_today": 0, "_rate": 0,
    }
