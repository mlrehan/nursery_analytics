"""Admin endpoints: manage users and configure each role's dashboard widgets."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import require_admin
from app.core.security import hash_password
from app.models.auth import (
    DashboardModule,
    DashboardWidget,
    Permission,
    Role,
    RolePermission,
    RoleWidgetAccess,
    User,
)
from app.schemas.auth import (
    PasswordSet,
    PermissionOut,
    RoleOut,
    RolePermissionToggle,
    RoleWidgetToggle,
    UserAdminUpdate,
    UserCreate,
    UserOut,
)

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
        phone=payload.phone, job_title=payload.job_title,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user, attribute_names=["role"])
    return user


@router.put("/users/{user_id}", response_model=UserOut)
async def update_user(user_id: int, payload: UserAdminUpdate, db: AsyncSession = Depends(get_db)) -> User:
    user = await db.scalar(select(User).where(User.id == user_id).options(selectinload(User.role)))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"]:
        data["email"] = data["email"].lower()
        clash = await db.scalar(select(User).where(User.email == data["email"], User.id != user_id))
        if clash:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
    for field, value in data.items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user, attribute_names=["role"])
    return user


@router.post("/users/{user_id}/password")
async def set_password(user_id: int, payload: PasswordSet, db: AsyncSession = Depends(get_db)) -> dict:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if len(payload.password) < 6:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password too short")
    user.hashed_password = hash_password(payload.password)
    await db.commit()
    return {"ok": True}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if user_id == admin_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own account")
    user = await db.scalar(select(User).where(User.id == user_id).options(selectinload(User.role)))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.role and user.role.slug == "admin":
        admin_count = await db.scalar(
            select(func.count()).select_from(User).join(Role).where(Role.slug == "admin", User.is_active.is_(True))
        )
        if admin_count <= 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete the last admin")
    await db.delete(user)
    await db.commit()
    return {"ok": True}


# ─── Roles & permissions ──────────────────────────────────────────────────────
@router.get("/permissions", response_model=list[PermissionOut])
async def list_permissions(db: AsyncSession = Depends(get_db)) -> list[Permission]:
    return list((await db.scalars(select(Permission).order_by(Permission.code))).all())


@router.get("/roles/{role_id}/permissions")
async def role_permissions(role_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    role = await db.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    granted = set((await db.scalars(
        select(Permission.code).join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role_id)
    )).all())
    all_perms = (await db.scalars(select(Permission).order_by(Permission.code))).all()
    return {
        "role": RoleOut.model_validate(role),
        "permissions": [
            {"code": p.code, "description": p.description, "granted": p.code in granted}
            for p in all_perms
        ],
    }


@router.post("/roles/permissions")
async def toggle_role_permission(payload: RolePermissionToggle, db: AsyncSession = Depends(get_db)) -> dict:
    perm = await db.scalar(select(Permission).where(Permission.code == payload.code))
    if perm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    existing = await db.scalar(
        select(RolePermission).where(
            (RolePermission.role_id == payload.role_id) & (RolePermission.permission_id == perm.id)
        )
    )
    if payload.granted and existing is None:
        db.add(RolePermission(role_id=payload.role_id, permission_id=perm.id))
    elif not payload.granted and existing is not None:
        await db.delete(existing)
    await db.commit()
    return {"role_id": payload.role_id, "code": payload.code, "granted": payload.granted}
