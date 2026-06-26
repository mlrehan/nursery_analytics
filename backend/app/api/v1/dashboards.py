"""Config-driven dashboard endpoints.

``/dashboards/me`` returns the modules + widgets the logged-in user's role is
allowed to see (composed from role_widget_access). ``/dashboards/{key}/data``
returns the computed analytics payload for one module, scoped by role.
"""
from __future__ import annotations

import io
import secrets
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.common import scope_for
from app.analytics.registry import compute_module
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user, get_user_permissions
from app.models.auth import DashboardModule, DashboardWidget, RoleWidgetAccess, User
from app.models.dimensions import Site
from app.models.settings import AppSettings
from app.models.share import ShareLink
from app.reports.pdf import build_report
from app.schemas.auth import MeDashboard, ModuleWithWidgets, RoleOut, UserOut, WidgetOut

PERIOD_LABEL = {7: "Last 7 days", 30: "Last 30 days", 90: "Last 90 days",
                180: "Last 6 months", 365: "Last 12 months"}

router = APIRouter(prefix="/dashboards", tags=["dashboards"])

# Tiny in-process TTL cache so re-navigation / refresh is instant. Keyed by the
# user + module + active filters; short TTL keeps data fresh.
_CACHE: dict[tuple, tuple[float, dict]] = {}
_TTL_SECONDS = 20


@router.get("/me", response_model=MeDashboard)
async def my_dashboards(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> MeDashboard:
    perms = await get_user_permissions(user, db)

    rows = (
        await db.execute(
            select(DashboardModule, DashboardWidget, RoleWidgetAccess)
            .join(DashboardWidget, DashboardWidget.module_id == DashboardModule.id)
            .join(
                RoleWidgetAccess,
                (RoleWidgetAccess.widget_id == DashboardWidget.id)
                & (RoleWidgetAccess.role_id == user.role_id),
            )
            .where(RoleWidgetAccess.is_enabled.is_(True))
            .order_by(DashboardModule.sort_order, RoleWidgetAccess.position, DashboardWidget.sort_order)
        )
    ).all()

    modules: dict[str, ModuleWithWidgets] = {}
    for module, widget, _access in rows:
        if f"view.{module.key}" not in perms:
            continue
        mod = modules.get(module.key)
        if mod is None:
            mod = ModuleWithWidgets(
                key=module.key, name=module.name, icon=module.icon,
                description=module.description, sort_order=module.sort_order, widgets=[],
            )
            modules[module.key] = mod
        mod.widgets.append(WidgetOut.model_validate(widget))

    ordered = sorted(modules.values(), key=lambda m: m.sort_order)
    return MeDashboard(
        user=UserOut(
            id=user.id, email=user.email, full_name=user.full_name,
            role=RoleOut.model_validate(user.role), site_id=user.site_id,
            is_active=user.is_active, last_login_at=user.last_login_at,
        ),
        permissions=sorted(perms),
        modules=ordered,
    )


@router.get("/filters")
async def available_filters(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    """Filter options for the dashboard toolbar, scoped to what the user may see."""
    scope = scope_for(user)
    stmt = select(Site.id, Site.name, Site.borough).order_by(Site.name)
    if scope.site_id:
        stmt = stmt.where(Site.id == scope.site_id)
    sites = [{"id": r.id, "name": r.name, "borough": r.borough} for r in (await db.execute(stmt)).all()]
    return {
        "sites": sites,
        "can_pick_site": scope.all_sites,
        "periods": [
            {"value": 7, "label": "7 days"},
            {"value": 30, "label": "30 days"},
            {"value": 90, "label": "90 days"},
            {"value": 365, "label": "12 months"},
        ],
        "default_period": 90,
    }


@router.get("/{module_key}/data")
async def module_data(
    module_key: str,
    site_id: int | None = Query(None, description="Filter to one site (privileged roles only)"),
    days: int | None = Query(None, description="Period window: 7|30|90|180|365"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    perms = await get_user_permissions(user, db)
    if f"view.{module_key}" not in perms:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted for this module")
    scope = scope_for(user, site_id=site_id, days=days)

    cache_key = (user.id, module_key, scope.site_id, scope.child_id, scope.window_days)
    now = time.monotonic()
    hit = _CACHE.get(cache_key)
    if hit and now - hit[0] < _TTL_SECONDS:
        data, cached = hit[1], True
    else:
        data = await compute_module(module_key, db, scope)
        _CACHE[cache_key] = (now, data)
        cached = False

    return {
        "module": module_key,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cached": cached,
        "scope": {"site_id": scope.site_id, "child_id": scope.child_id,
                  "all_sites": scope.all_sites, "window_days": scope.window_days},
        "data": data,
    }


def _share_base(request: Request) -> str:
    return (settings.PUBLIC_BASE_URL.rstrip("/") + "/") if settings.PUBLIC_BASE_URL else str(request.base_url)


@router.post("/{module_key}/share-link")
async def create_share_link(
    module_key: str,
    request: Request,
    site_id: int | None = Query(None),
    days: int | None = Query(None),
    expires_days: int = Query(30, description="Link lifetime in days; 0 = never expires"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mint a PUBLIC, no-login share link for this dashboard view (managed, revocable)."""
    perms = await get_user_permissions(user, db)
    if f"view.{module_key}" not in perms:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted for this module")
    scope = scope_for(user, site_id=site_id, days=days)   # clamps to what the user may see
    module = await db.scalar(select(DashboardModule).where(DashboardModule.key == module_key))

    token = secrets.token_urlsafe(24)
    expires_at = (datetime.now(timezone.utc) + timedelta(days=expires_days)) if expires_days and expires_days > 0 else None
    db.add(ShareLink(
        token=token, module_key=module_key, site_id=scope.site_id, child_id=scope.child_id,
        window_days=scope.window_days, label=(module.name if module else module_key),
        created_by=user.id, expires_at=expires_at,
    ))
    await db.commit()
    base = _share_base(request)
    return {"token": token, "url": f"{base}share/{token}", "expires_days": expires_days,
            "expires_at": expires_at.isoformat() if expires_at else None}


@router.get("/{module_key}/report.pdf")
async def module_report_pdf(
    module_key: str,
    site_id: int | None = Query(None),
    days: int | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Branded, server-generated PDF of one dashboard — same data as the screen."""
    perms = await get_user_permissions(user, db)
    if f"view.{module_key}" not in perms:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted for this module")
    scope = scope_for(user, site_id=site_id, days=days)

    module = await db.scalar(select(DashboardModule).where(DashboardModule.key == module_key))
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")

    rows = (
        await db.execute(
            select(DashboardWidget)
            .join(RoleWidgetAccess, (RoleWidgetAccess.widget_id == DashboardWidget.id)
                  & (RoleWidgetAccess.role_id == user.role_id))
            .where(DashboardWidget.module_id == module.id, RoleWidgetAccess.is_enabled.is_(True))
            .order_by(RoleWidgetAccess.position, DashboardWidget.sort_order)
        )
    ).scalars().all()
    widgets = [{"key": w.key, "title": w.title, "viz": w.viz_type} for w in rows]

    data = await compute_module(module_key, db, scope)

    branding = await db.get(AppSettings, 1)
    brand_name = (branding.brand_name if branding else None) or "Nursery Analytics"

    site_label = "All sites"
    if scope.site_id:
        s = await db.get(Site, scope.site_id)
        site_label = s.name if s else f"Site {scope.site_id}"
    scope_label = f"{site_label}  ·  {PERIOD_LABEL.get(scope.window_days, f'Last {scope.window_days} days')}"

    pdf = build_report(brand_name=brand_name, scope_label=scope_label,
                       module_name=module.name, widgets=widgets, data=data)
    fname = f"{brand_name.replace(' ', '_')}_{module_key}_{datetime.now():%Y%m%d}.pdf"
    return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{fname}"'})
