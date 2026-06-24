"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Optional: run migrations + seed in-process (also runnable via `python -m app.cli`).
    if settings.RUN_MIGRATIONS_ON_STARTUP:
        try:
            from app.migrations.runner import run_migrations
            run_migrations()
        except Exception as exc:  # pragma: no cover
            print(f"[startup] migration error: {exc}")
    if settings.SEED_ON_STARTUP:
        try:
            from app.seed.seed import seed
            seed(force=False)
        except Exception as exc:  # pragma: no cover
            print(f"[startup] seed error: {exc}")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Enterprise analytics dashboards for UK day-nursery operators.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok", "service": settings.PROJECT_NAME, "env": settings.ENVIRONMENT}
