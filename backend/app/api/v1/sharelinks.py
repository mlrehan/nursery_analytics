"""Manage your public share links — list, revoke, delete."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user, get_user_permissions
from app.models.auth import User
from app.models.share import ShareLink

router = APIRouter(prefix="/share-links", tags=["share-links"])


def _base(request: Request) -> str:
    return (settings.PUBLIC_BASE_URL.rstrip("/") + "/") if settings.PUBLIC_BASE_URL else str(request.base_url)


def _status(link: ShareLink) -> str:
    if link.revoked:
        return "revoked"
    if link.expires_at and link.expires_at < datetime.now(timezone.utc):
        return "expired"
    return "active"


async def _owner_or_admin(link: ShareLink, user: User, db: AsyncSession) -> bool:
    if link.created_by == user.id:
        return True
    return "admin.manage_users" in await get_user_permissions(user, db)


@router.get("")
async def list_my_links(request: Request, user: User = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = (await db.scalars(
        select(ShareLink).where(ShareLink.created_by == user.id).order_by(ShareLink.created_at.desc())
    )).all()
    base = _base(request)
    return [{
        "token": r.token,
        "url": f"{base}share/{r.token}",
        "module_key": r.module_key,
        "label": r.label or r.module_key,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "expires_at": r.expires_at.isoformat() if r.expires_at else None,
        "revoked": r.revoked,
        "status": _status(r),
        "view_count": r.view_count,
        "last_viewed_at": r.last_viewed_at.isoformat() if r.last_viewed_at else None,
    } for r in rows]


@router.post("/{token}/revoke")
async def revoke_link(token: str, user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)) -> dict:
    link = await db.get(ShareLink, token)
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")
    if not await _owner_or_admin(link, user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your link")
    link.revoked = True
    await db.commit()
    return {"token": token, "revoked": True}


@router.delete("/{token}")
async def delete_link(token: str, user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)) -> dict:
    link = await db.get(ShareLink, token)
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")
    if not await _owner_or_admin(link, user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your link")
    await db.delete(link)
    await db.commit()
    return {"token": token, "deleted": True}
