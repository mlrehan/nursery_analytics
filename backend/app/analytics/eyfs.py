"""Child Development / EYFS analytics."""
from __future__ import annotations

import datetime as dt

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.common import Scope, fetch_df, gauge, kpi, pct, safe_div

AREAS = ["communication", "physical", "pse", "literacy", "numeracy"]
AREA_LABELS = {"communication": "Communication", "physical": "Physical", "pse": "PSE",
               "literacy": "Literacy", "numeracy": "Numeracy"}


async def compute(db: AsyncSession, scope: Scope) -> dict:
    today = dt.date.today()
    p = scope.params
    child_clause = " AND o.child_id = :scope_child " if scope.child_id else " "

    obs = await fetch_df(
        db,
        f"""SELECT o.child_id, o.observation_date, o.area, o.status, o.on_track, c.dob
            FROM fact_eyfs_observation o JOIN dim_child c ON c.id = o.child_id
            WHERE 1=1 {scope.site_clause('o')} {child_clause}""",
        p,
    )
    if obs.empty:
        return _empty()

    win = scope.window_days
    obs_recent = int((pd.to_datetime(obs["observation_date"]).dt.date >= (today - dt.timedelta(days=win))).sum())

    # latest status per child+area, then % on track
    obs_sorted = obs.sort_values("observation_date")
    latest = obs_sorted.groupby(["child_id", "area"]).tail(1)
    on_track_pct = pct(safe_div(int(latest["on_track"].sum()), len(latest)) * 100)
    at_risk = int(latest[~latest["on_track"]]["child_id"].nunique())

    # by area bar (% on track)
    by_area = {"categories": [], "series": [{"name": "On Track %", "data": []}]}
    for a in AREAS:
        sub = latest[latest["area"] == a]
        by_area["categories"].append(AREA_LABELS[a])
        by_area["series"][0]["data"].append(pct(safe_div(int(sub["on_track"].sum()), len(sub)) * 100) if len(sub) else 0)

    # by age group stacked (status mix)
    latest = latest.copy()
    ages = (pd.Timestamp(today) - pd.to_datetime(latest["dob"])).dt.days / 365.25
    latest["age_band"] = pd.cut(ages, bins=[0, 2, 3, 4, 99], right=False,
                                labels=["0-2y", "2-3y", "3-4y", "4-5y"])
    bands = ["0-2y", "2-3y", "3-4y", "4-5y"]
    by_age = {"categories": bands, "stack": True,
              "series": [{"name": s.capitalize(), "data": []} for s in ["emerging", "expected", "exceeding"]]}
    for i, status in enumerate(["emerging", "expected", "exceeding"]):
        for band in bands:
            sub = latest[(latest["age_band"] == band) & (latest["status"] == status)]
            by_age["series"][i]["data"].append(int(len(sub)))

    # heatmap area x age band on-track %
    heat = {"x": bands, "y": [AREA_LABELS[a] for a in AREAS], "data": [], "max": 100}
    for yi, a in enumerate(AREAS):
        for xi, band in enumerate(bands):
            sub = latest[(latest["area"] == a) & (latest["age_band"] == band)]
            val = round(safe_div(int(sub["on_track"].sum()), len(sub)) * 100, 0) if len(sub) else 0
            heat["data"].append([xi, yi, int(val)])

    return {
        "eyfs.on_track": gauge(on_track_pct, "Children On Track"),
        "eyfs.observations": kpi(obs_recent, "Observations", sub=f"last {win} days"),
        "eyfs.at_risk": kpi(at_risk, "At-Risk Children", status="warn" if at_risk else "ok"),
        "eyfs.by_area": by_area,
        "eyfs.by_age": by_age,
        "eyfs.heatmap": heat,
        "_on_track": on_track_pct, "_at_risk": at_risk,
    }


def _empty() -> dict:
    return {
        "eyfs.on_track": gauge(0, "Children On Track"),
        "eyfs.observations": kpi(0, "Observations"), "eyfs.at_risk": kpi(0, "At-Risk Children"),
        "eyfs.by_area": {"categories": [], "series": []},
        "eyfs.by_age": {"categories": [], "series": [], "stack": True},
        "eyfs.heatmap": {"x": [], "y": [], "data": [], "max": 100},
        "_on_track": 0, "_at_risk": 0,
    }
