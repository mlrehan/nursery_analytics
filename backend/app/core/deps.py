"""Auth / RBAC dependencies."""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_token
from app.models.auth import Permission, RolePermission, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    creds_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise creds_exc
    user_id = payload.get("sub")
    if user_id is None:
        raise creds_exc
    user = await db.scalar(
        select(User).where(User.id == int(user_id)).options(selectinload(User.role))
    )
    if user is None or not user.is_active:
        raise creds_exc
    return user


async def get_user_permissions(user: User, db: AsyncSession) -> set[str]:
    rows = await db.scalars(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == user.role_id)
    )
    return set(rows.all())


def require_permission(code: str):
    """Dependency factory enforcing a single permission code.

    Admins are granted every permission at seed time, so they pass naturally.
    """

    async def _dep(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> User:
        perms = await get_user_permissions(user, db)
        if code not in perms:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted")
        return user

    return _dep


def require_module(module_key: str):
    """Enforce 'view.<module_key>' permission for a dashboard module endpoint."""
    return require_permission(f"view.{module_key}")


async def require_admin(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> User:
    perms = await get_user_permissions(user, db)
    if "admin.manage_dashboards" not in perms and "admin.manage_users" not in perms:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user
