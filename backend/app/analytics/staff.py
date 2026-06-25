"""Staff Management analytics."""
from __future__ import annotations

import datetime as dt

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.common import Scope, fetch_df, gauge, kpi, pct, safe_div


async def compute(db: AsyncSession, scope: Scope) -> dict:
    today = dt.date.today()
    p = scope.params
    sc = scope.site_clause()

    # shifts over the selected period
    win = scope.window_days
    win_lbl = f"last {win} days"
    shifts = await fetch_df(
        db,
        f"""SELECT s.staff_id, s.date, s.hours_scheduled, s.hours_worked, s.overtime_hours,
                   s.absent, s.room_id, st.hourly_rate, st.qualification_level, st.is_agency
            FROM fact_staff_shift s JOIN dim_staff st ON st.id = s.staff_id
            WHERE 1=1 {scope.site_clause('s')} AND s.date >= :dwin""",
        {**p, "dwin": today - dt.timedelta(days=win)},
    )
    last_shift_date = shifts["date"].max() if not shifts.empty else today
    on_duty = int(shifts[(shifts["date"] == last_shift_date) & (~shifts["absent"])]["staff_id"].nunique()) if not shifts.empty else 0

    shiftsw = shifts  # already restricted to the active window
    if not shiftsw.empty:
        absence_rate = pct(safe_div(int(shiftsw["absent"].sum()), len(shiftsw)) * 100)
        overtime = round(float(shiftsw["overtime_hours"].astype(float).sum()), 1)
        worked = shiftsw.loc[~shiftsw["absent"]]
        payroll = round(float((worked["hours_worked"].astype(float) * worked["hourly_rate"].astype(float)).sum()), 2)
        agency_hours = float(shiftsw.loc[shiftsw["is_agency"], "hours_worked"].astype(float).sum())
        total_hours = float(shiftsw["hours_worked"].astype(float).sum())
        agency_pct = pct(safe_div(agency_hours, total_hours) * 100)
    else:
        absence_rate = overtime = payroll = agency_pct = 0

    # ratio compliance: per room on last_shift_date, children present vs staff on duty
    ratio_room = {"categories": [], "series": [{"name": "Children/Staff", "data": []},
                                               {"name": "Required", "data": []}]}
    rooms = await fetch_df(
        db, f"SELECT id, name, room_type, required_ratio FROM dim_room WHERE 1=1 {scope.site_clause()}", p)
    att_today = await fetch_df(
        db, f"SELECT room_id, COUNT(*) AS present FROM fact_attendance WHERE date = :d AND status='present' {sc} GROUP BY room_id",
        {**p, "d": last_shift_date})
    present_map = dict(zip(att_today["room_id"], att_today["present"])) if not att_today.empty else {}
    staff_room = shifts[(shifts["date"] == last_shift_date) & (~shifts["absent"])] if not shifts.empty else pd.DataFrame()
    staff_map = staff_room.groupby("room_id")["staff_id"].nunique().to_dict() if not staff_room.empty else {}
    compliant = total_rooms = 0
    if not rooms.empty:
        for _, rm in rooms.iterrows():
            present = present_map.get(rm["id"], 0)
            staff_n = max(staff_map.get(rm["id"], 0), 1)
            actual_ratio = safe_div(present, staff_n)
            ratio_room["categories"].append(rm["name"])
            ratio_room["series"][0]["data"].append(round(actual_ratio, 1))
            ratio_room["series"][1]["data"].append(int(rm["required_ratio"]))
            total_rooms += 1
            if actual_ratio <= rm["required_ratio"]:
                compliant += 1
    ratio_compliance = pct(safe_div(compliant, total_rooms) * 100) if total_rooms else 100.0

    # qualification mix
    quals = await fetch_df(
        db, f"SELECT qualification_level, COUNT(*) AS n FROM dim_staff WHERE 1=1 {scope.site_clause()} GROUP BY qualification_level",
        p)
    qmap = {0: "Unqualified", 2: "Level 2", 3: "Level 3", 6: "Level 6 (EYP)"}
    quals_pie = {"data": [{"name": qmap.get(int(r["qualification_level"]), f"L{int(r['qualification_level'])}"),
                           "value": int(r["n"])} for _, r in quals.iterrows()]} if not quals.empty else {"data": []}

    # utilisation trend (weekly worked vs scheduled)
    util = {"x": [], "series": [{"name": "Worked", "data": []}, {"name": "Scheduled", "data": []}]}
    if not shifts.empty:
        sdf = shifts.copy()
        sdf["week"] = pd.to_datetime(sdf["date"]).dt.to_period("W").dt.start_time
        wk = sdf.groupby("week").agg(worked=("hours_worked", "sum"), sched=("hours_scheduled", "sum")).reset_index()
        wk = wk.tail(8)
        util["x"] = [w.strftime("%d %b") for w in wk["week"]]
        util["series"][0]["data"] = [round(float(v), 1) for v in wk["worked"]]
        util["series"][1]["data"] = [round(float(v), 1) for v in wk["sched"]]

    return {
        "staff.on_duty": kpi(on_duty, "On Duty Today", sub="as of today"),
        "staff.ratio": gauge(ratio_compliance, "Ratio Compliance"),
        "staff.absence": kpi(absence_rate, "Absence Rate", unit="%", sub=win_lbl,
                             status="warn" if absence_rate > 8 else "ok"),
        "staff.overtime": kpi(overtime, "Overtime Hours", sub=win_lbl),
        "staff.ratio_room": ratio_room,
        "staff.quals": quals_pie,
        "staff.utilisation": util,
        "staff.payroll": kpi(payroll, "Payroll Cost", unit="£", sub=win_lbl),
        "staff.agency": kpi(agency_pct, "Agency Usage", unit="%"),
        "_ratio_compliance": ratio_compliance, "_on_duty": on_duty,
    }
