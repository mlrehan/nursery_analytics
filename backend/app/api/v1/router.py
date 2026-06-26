"""Aggregates all v1 routers."""
from fastapi import APIRouter

from app.api.v1 import admin, auth, dashboards, public, search, settings

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(dashboards.router)
api_router.include_router(admin.router)
api_router.include_router(search.router)
api_router.include_router(settings.router)
api_router.include_router(public.router)
