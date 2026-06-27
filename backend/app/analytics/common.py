"""Shared analytics helpers: dataframe loading, scoping and payload builders.

All KPI/chart computation uses pandas + numpy over data pulled through the async
session. Each module function returns ``dict[widget_key, payload]`` where payload
shape is determined by the widget's ``viz_type`` (see PAYLOAD CONTRACT below).

PAYLOAD CONTRACT
  kpi          -> {value, unit, label, delta?, sub?, status?}
  gauge        -> {value, max, label, unit?}
  line         -> {x: [...], series: [{name, data}]}
  bar          -> {categories: [...], series: [{name, data}]}
  stacked_bar  -> {categories: [...], series: [{name, data}], stack: true}
  pie          -> {data: [{name, value}]}
  heatmap      -> {x: [...], y: [...], data: [[xi, yi, value], ...], max}
  funnel       -> {data: [{name, value}]}
  table        -> {columns: [...], rows: [[...]]}
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import User


@dataclass
class Scope:
    """Row-level scoping + active filters derived from the user and request."""
    site_id: int | None = None      # restrict to a single site
    child_id: int | None = None     # restrict to a single child (parents)
    all_sites: bool = True
    window_days: int = 90           # global period filter for time-window widgets

    def site_clause(self, alias: str = "") -> str:
        """Filter a fact/dimension that has a `site_id` foreign key."""
        col = f"{alias}.site_id" if alias else "site_id"
        return f" AND {col} = :scope_site " if self.site_id else " "

    def site_pk_clause(self, alias: str = "") -> str:
        """Filter the `dim_site` table itself, whose primary key is `id`."""
        col = f"{alias}.id" if alias else "id"
        return f" AND {col} = :scope_site " if self.site_id else " "

    @property
    def params(self) -> dict:
        p: dict = {}
        if self.site_id:
            p["scope_site"] = self.site_id
        if self.child_id:
            p["scope_child"] = self.child_id
        return p


def scope_for(user: User, site_id: int | None = None, days: int | None = None) -> Scope:
    """Build scope from the user's role, then apply request filters.

    Privileged roles (admin/management/accounts) may narrow to any site via the
    `site_id` filter (this powers click-to-filter). Site-bound roles
    (teacher/parent) are locked to their own site and ignore the override.
    """
    slug = user.role.slug if user.role else ""
    if slug in ("admin", "management", "accounts"):
        scope = Scope(all_sites=True)
        if site_id:
            scope.site_id = site_id
            scope.all_sites = False
    elif slug == "parent":
        scope = Scope(site_id=user.site_id, child_id=user.linked_child_id, all_sites=False)
    else:  # teacher / site-bound
        scope = Scope(site_id=user.site_id, all_sites=False)

    if days and days in (7, 30, 90, 180, 365):
        scope.window_days = days
    return scope


async def fetch_df(db: AsyncSession, sql: str, params: dict | None = None) -> pd.DataFrame:
    result = await db.execute(text(sql), params or {})
    rows = result.fetchall()
    return pd.DataFrame(rows, columns=list(result.keys()))


# ─── small formatting helpers ─────────────────────────────────────────────────
def gbp(value: float) -> dict:
    return {"value": round(float(value), 2), "unit": "£"}


def pct(value: float) -> float:
    return round(float(value), 1)


def safe_div(a: float, b: float) -> float:
    return float(a) / float(b) if b else 0.0


def kpi(value, label: str, unit: str = "", delta: float | None = None,
        sub: str | None = None, status: str | None = None,
        spark: list | None = None, accent: str | None = None,
        drill: dict | None = None) -> dict:
    """KPI card payload. `delta` is a % vs previous period; `spark` is a small
    series for the mini sparkline; `accent` hints the icon-chip colour; `drill`
    is an optional {title, columns, rows} table shown when the card is clicked."""
    out = {"value": value, "label": label, "unit": unit}
    if delta is not None:
        out["delta"] = round(float(delta), 1)
    if sub:
        out["sub"] = sub
    if status:
        out["status"] = status
    if spark:
        out["spark"] = [round(float(x), 2) for x in spark]
    if accent:
        out["accent"] = accent
    if drill and drill.get("rows"):
        out["drill"] = drill
    return out


def gauge(value: float, label: str, max_: float = 100, unit: str = "%") -> dict:
    return {"value": round(float(value), 1), "max": max_, "label": label, "unit": unit}


def linear_forecast(series: list[float], periods: int) -> list[float]:
    """Simple least-squares linear forecast (numpy) for the next ``periods``."""
    y = np.asarray(series, dtype=float)
    if len(y) < 2:
        return [float(y[-1]) if len(y) else 0.0] * periods
    x = np.arange(len(y))
    slope, intercept = np.polyfit(x, y, 1)
    fx = np.arange(len(y), len(y) + periods)
    return [float(max(0.0, slope * xi + intercept)) for xi in fx]


def month_labels(months: list[dt.date]) -> list[str]:
    return [m.strftime("%b %y") for m in months]
