"""Admin endpoints: manage users and configure each role's dashboard widgets."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import require_admin
from app.core.security import hash_password
from app.models.auth import (
    DashboardModule,
    DashboardWidget,
    Role,
    RoleWidgetAccess,
    User,
)
from app.schemas.auth import RoleOut, RoleWidgetToggle, UserCreate, UserOut

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/roles", response_model=list[RoleOut])
async def list_roles(db: AsyncSession = Depends(get_db)) -> list[Role]:
    return list((await db.scalars(select(Role).order_by(Role.id))).all())


@router.get("/dashboard-config")
async def dashboard_config(role_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    """Full widget catalogue annotated with whether the given role currently sees it.

    Lets the admin UI render a per-role matrix of toggles across all 15 modules.
    """
    role = await db.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    access_rows = (
        await db.execute(
            select(RoleWidgetAccess.widget_id, RoleWidgetAccess.is_enabled)
            .where(RoleWidgetAccess.role_id == role_id)
        )
    ).all()
    enabled = {wid: en for wid, en in access_rows}

    modules = (
        await db.scalars(
            select(DashboardModule).options(selectinload(DashboardModule.widgets)).order_by(DashboardModule.sort_order)
        )
    ).all()

    out = []
    for m in modules:
        widgets = sorted(m.widgets, key=lambda w: w.sort_order)
        out.append({
            "key": m.key, "name": m.name, "icon": m.icon,
            "widgets": [
                {"key": w.key, "title": w.title, "viz_type": w.viz_type,
                 "is_enabled": bool(enabled.get(w.id, False))}
                for w in widgets
            ],
        })
    return {"role": RoleOut.model_validate(role), "modules": out}


@router.post("/dashboard-config/toggle")
async def toggle_widget(payload: RoleWidgetToggle, db: AsyncSession = Depends(get_db)) -> dict:
    """Admin enables/removes a single widget for a role (upsert into role_widget_access)."""
    widget = await db.scalar(select(DashboardWidget).where(DashboardWidget.key == payload.widget_key))
    if widget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found")

    access = await db.scalar(
        select(RoleWidgetAccess).where(
            (RoleWidgetAccess.role_id == payload.role_id) & (RoleWidgetAccess.widget_id == widget.id)
        )
    )
    if access is None:
        access = RoleWidgetAccess(
            role_id=payload.role_id, widget_id=widget.id,
            is_enabled=payload.is_enabled, position=widget.sort_order,
        )
        db.add(access)
    else:
        access.is_enabled = payload.is_enabled
    await db.commit()
    return {"role_id": payload.role_id, "widget_key": payload.widget_key, "is_enabled": payload.is_enabled}


@router.get("/users", response_model=list[UserOut])
async def list_users(db: AsyncSession = Depends(get_db)) -> list[User]:
    return list((await db.scalars(select(User).options(selectinload(User.role)).order_by(User.id))).all())


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> User:
    exists = await db.scalar(select(User).where(User.email == payload.email.lower()))
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(
        email=payload.email.lower(), full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role_id=payload.role_id, site_id=payload.site_id, is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user, attribute_names=["role"])
    return user
