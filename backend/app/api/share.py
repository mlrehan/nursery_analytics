"""Public, crawler-friendly share pages.

Social/chat apps (Facebook, X, WhatsApp, LinkedIn) fetch the shared URL and read
Open Graph / Twitter-card meta tags to build a rich preview. We serve a small public
page here with proper tags + a branded preview image (brand + dashboard name only —
never confidential data), then redirect human visitors to the public read-only
dashboard view (/s/{token}) which needs NO login.

Mounted at the site root (no /api prefix):  https://your-domain/share/{token}
"""
from __future__ import annotations

import html

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.auth import DashboardModule
from app.models.settings import AppSettings
from app.models.share import ShareLink

router = APIRouter(tags=["share"])

TAGLINE_FALLBACK = "Early Years Intelligence"
DESCRIPTION = ("Live nursery analytics — occupancy, revenue, attendance, EYFS progress, "
               "staffing and compliance, in one enterprise dashboard.")


async def _brand_and_module(token: str) -> tuple[str, str, str]:
    async with AsyncSessionLocal() as db:
        s = await db.get(AppSettings, 1)
        brand = (s.brand_name if s else None) or "Nursery Analytics"
        tagline = (s.brand_tagline if s and s.brand_tagline else TAGLINE_FALLBACK)
        module_name = "Analytics Dashboard"
        link = await db.get(ShareLink, token)
        if link:
            if link.label:
                module_name = link.label
            else:
                m = await db.scalar(select(DashboardModule).where(DashboardModule.key == link.module_key))
                module_name = m.name if m else module_name
    return brand, tagline, module_name


def _base(request: Request) -> str:
    return (settings.PUBLIC_BASE_URL.rstrip("/") + "/") if settings.PUBLIC_BASE_URL else str(request.base_url)


@router.get("/share/{token}", response_class=HTMLResponse)
async def share_page(token: str, request: Request) -> HTMLResponse:
    brand, tagline, module_name = await _brand_and_module(token)

    base = _base(request)
    page_url = f"{base}share/{token}"
    img_url = f"{base}share/{token}/image.png"
    view_url = f"{base}s/{token}"                       # public, no-login view
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
<meta http-equiv="refresh" content="0; url={e(view_url)}"/>
<style>body{{font-family:Inter,system-ui,sans-serif;background:#0b1020;color:#e8edf9;
display:grid;place-items:center;height:100vh;margin:0}}a{{color:#8ab4ff}}</style>
</head><body>
<div style="text-align:center">
<p style="font-size:20px;font-weight:700">{e(title)}</p>
<p>Opening report… <a href="{e(view_url)}">Continue</a></p>
</div>
<script>location.replace({view_url!r});</script>
</body></html>"""
    return HTMLResponse(page)


@router.get("/share/{token}/image.png")
async def share_image(token: str) -> Response:
    brand, tagline, module_name = await _brand_and_module(token)
    try:
        from app.reports.og_image import build_og_image
        png = build_og_image(brand, tagline, module_name)
        return Response(png, media_type="image/png", headers={"Cache-Control": "public, max-age=3600"})
    except Exception as exc:  # pragma: no cover - never fail the share card
        return Response(f"image error: {exc}".encode(), media_type="text/plain", status_code=500)
