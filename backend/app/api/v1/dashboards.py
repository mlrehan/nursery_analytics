"""Config-driven dashboard endpoints.

``/dashboards/me`` returns the modules + widgets the logged-in user's role is
allowed to see (composed from role_widget_access). ``/dashboards/{key}/data``
returns the computed analytics payload for one module, scoped by role.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.common import scope_for
from app.analytics.registry import compute_module
from app.core.database import get_db
from app.core.deps import get_current_user, get_user_permissions
from app.models.auth import DashboardModule, DashboardWidget, RoleWidgetAccess, User
from app.schemas.auth import MeDashboard, ModuleWithWidgets, RoleOut, UserOut, WidgetOut

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


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


@router.get("/{module_key}/data")
async def module_data(
    module_key: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    perms = await get_user_permissions(user, db)
    if f"view.{module_key}" not in perms:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted for this module")
    scope = scope_for(user)
    data = await compute_module(module_key, db, scope)
    return {
        "module": module_key,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": {"site_id": scope.site_id, "child_id": scope.child_id, "all_sites": scope.all_sites},
        "data": data,
    }
