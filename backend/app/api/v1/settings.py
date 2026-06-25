"""White-label branding: public read (so the login screen can brand itself),
admin-only write."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.settings import AppSettings
from app.schemas.auth import BrandingOut, BrandingUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


async def _get_or_create(db: AsyncSession) -> AppSettings:
    row = await db.get(AppSettings, 1)
    if row is None:
        row = AppSettings(id=1, brand_name="Nursery Analytics", brand_tagline="ENTERPRISE · LONDON")
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


@router.get("/branding", response_model=BrandingOut)
async def get_branding(db: AsyncSession = Depends(get_db)) -> AppSettings:
    """Public — used by the login screen and app shell before/after auth."""
    return await _get_or_create(db)


@router.put("/branding", response_model=BrandingOut, dependencies=[Depends(require_admin)])
async def update_branding(payload: BrandingUpdate, db: AsyncSession = Depends(get_db)) -> AppSettings:
    row = await _get_or_create(db)
    data = payload.model_dump(exclude_unset=True)
    # empty string => clear (fall back to default letter / favicon)
    for field in ("logo_url", "icon_url", "brand_tagline"):
        if field in data and data[field] == "":
            data[field] = None
    if data.get("brand_name") == "":
        data.pop("brand_name")  # never allow a blank product name
    for k, v in data.items():
        setattr(row, k, v)
    await db.commit()
    await db.refresh(row)
    return row
