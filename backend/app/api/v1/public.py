"""Public, no-login read-only dashboard data — authorised by a signed share token.

Anyone with the link can view the exact shared dashboard (module + filters baked
into the token). No user account or login required.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.analytics.common import Scope
from app.analytics.registry import compute_module
from app.core.database import AsyncSessionLocal
from app.core.security import decode_share_token
from app.models.auth import DashboardModule, DashboardWidget
from app.models.dimensions import Site
from app.models.settings import AppSettings

router = APIRouter(prefix="/public", tags=["public"])

PERIOD_LABEL = {7: "Last 7 days", 30: "Last 30 days", 90: "Last 90 days",
                180: "Last 6 months", 365: "Last 12 months"}


@router.get("/report")
async def public_report(token: str = Query(...)) -> dict:
    payload = decode_share_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This share link is invalid or has expired.")
    module_key = payload.get("m")
    scope = Scope(
        site_id=payload.get("site"),
        child_id=payload.get("child"),
        all_sites=payload.get("site") is None,
        window_days=payload.get("days") or 90,
    )

    async with AsyncSessionLocal() as db:
        module = await db.scalar(select(DashboardModule).where(DashboardModule.key == module_key))
        if module is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found.")
        rows = (
            await db.scalars(
                select(DashboardWidget).where(DashboardWidget.module_id == module.id)
                .order_by(DashboardWidget.sort_order)
            )
        ).all()
        widgets = [{"key": w.key, "title": w.title, "viz_type": w.viz_type,
                    "span": w.span, "description": w.description} for w in rows]

        data = await compute_module(module_key, db, scope)

        branding = await db.get(AppSettings, 1)
        brand_name = (branding.brand_name if branding else None) or "Nursery Analytics"
        logo_url = branding.logo_url if branding else None

        site_label = "All sites"
        if scope.site_id:
            s = await db.get(Site, scope.site_id)
            site_label = s.name if s else f"Site {scope.site_id}"

    period = PERIOD_LABEL.get(scope.window_days, f"Last {scope.window_days} days")
    return {
        "brand_name": brand_name,
        "logo_url": logo_url,
        "module_key": module_key,
        "module_name": module.name,
        "module_description": module.description,
        "scope_label": f"{site_label} · {period}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "widgets": widgets,
        "data": data,
    }
