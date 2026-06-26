"""Public, crawler-friendly share pages.

Social/chat apps (Facebook, X, WhatsApp, LinkedIn) fetch the shared URL and read
Open Graph / Twitter-card meta tags to build a rich preview. Our app is a private
SPA, so we serve a small public page here with proper tags + a branded preview
image (brand + dashboard name only — never confidential data), then redirect human
visitors into the app.

Mounted at the site root (no /api prefix), e.g.  https://your-domain/share/executive
"""
from __future__ import annotations

import html
import io

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.auth import DashboardModule
from app.models.settings import AppSettings

router = APIRouter(tags=["share"])

TAGLINE_FALLBACK = "Early Years Intelligence"
DESCRIPTION = ("Live nursery analytics — occupancy, revenue, attendance, EYFS progress, "
               "staffing and compliance, in one enterprise dashboard.")


async def _brand_and_module(module_key: str) -> tuple[str, str, str]:
    async with AsyncSessionLocal() as db:
        s = await db.get(AppSettings, 1)
        brand = (s.brand_name if s else None) or "Nursery Analytics"
        tagline = (s.brand_tagline if s and s.brand_tagline else TAGLINE_FALLBACK)
        m = await db.scalar(select(DashboardModule).where(DashboardModule.key == module_key))
        module_name = m.name if m else "Analytics Dashboard"
    return brand, tagline, module_name


@router.get("/share/{module_key}", response_class=HTMLResponse)
async def share_page(module_key: str, request: Request) -> HTMLResponse:
    brand, tagline, module_name = await _brand_and_module(module_key)
    # Prefer the configured public URL (reliable absolute HTTPS for OG); else derive.
    base = (settings.PUBLIC_BASE_URL.rstrip("/") + "/") if settings.PUBLIC_BASE_URL else str(request.base_url)
    page_url = f"{base}share/{module_key}"
    img_url = f"{base}share/{module_key}/image.png"
    app_url = f"{base}m/{module_key}"
    title = f"{brand} — {module_name}"

    e = html.escape
    page = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{e(title)}</title>
<meta name="description" content="{e(DESCRIPTION)}"/>
<meta property="og:type" content="website"/>
<meta property="og:site_name" content="{e(brand)}"/>
<meta property="og:title" content="{e(title)}"/>
<meta property="og:description" content="{e(DESCRIPTION)}"/>
<meta property="og:url" content="{e(page_url)}"/>
<meta property="og:image" content="{e(img_url)}"/>
<meta property="og:image:width" content="1200"/>
<meta property="og:image:height" content="630"/>
<meta name="twitter:card" content="summary_large_image"/>
<meta name="twitter:title" content="{e(title)}"/>
<meta name="twitter:description" content="{e(DESCRIPTION)}"/>
<meta name="twitter:image" content="{e(img_url)}"/>
<meta http-equiv="refresh" content="0; url={e(app_url)}"/>
<style>body{{font-family:Inter,system-ui,sans-serif;background:#0b1020;color:#e8edf9;
display:grid;place-items:center;height:100vh;margin:0}}a{{color:#8ab4ff}}</style>
</head><body>
<div style="text-align:center">
<p style="font-size:20px;font-weight:700">{e(title)}</p>
<p>Opening the dashboard… <a href="{e(app_url)}">Continue</a></p>
</div>
<script>location.replace({app_url!r});</script>
</body></html>"""
    return HTMLResponse(page)


@router.get("/share/{module_key}/image.png")
async def share_image(module_key: str) -> Response:
    brand, tagline, module_name = await _brand_and_module(module_key)
    try:
        from app.reports.og_image import build_og_image
        png = build_og_image(brand, tagline, module_name)
        return Response(png, media_type="image/png",
                        headers={"Cache-Control": "public, max-age=3600"})
    except Exception as exc:  # pragma: no cover - never fail the share card
        return Response(f"image error: {exc}".encode(), media_type="text/plain", status_code=500)
