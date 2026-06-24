"""Maps a dashboard module key to its analytics compute function."""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import (
    attendance,
    compliance,
    executive,
    eyfs,
    extras,
    finance,
    occupancy,
    staff,
)
from app.analytics.common import Scope

ComputeFn = Callable[[AsyncSession, Scope], Awaitable[dict]]

MODULE_COMPUTE: dict[str, ComputeFn] = {
    "executive": executive.compute,
    "occupancy": occupancy.compute,
    "finance": finance.compute,
    "staff": staff.compute,
    "compliance": compliance.compute,
    "attendance": attendance.compute,
    "eyfs": eyfs.compute,
    "nutrition": extras.nutrition,
    "parent_comms": extras.parent_comms,
    "multisite": extras.multisite,
    "analytics": extras.analytics,
    "alerts": extras.alerts,
    "operations": extras.operations,
    "mobile": extras.mobile,
    "ai": extras.ai,
}


async def compute_module(module_key: str, db: AsyncSession, scope: Scope) -> dict:
    fn = MODULE_COMPUTE.get(module_key)
    if fn is None:
        return {}
    data = await fn(db, scope)
    # strip internal cross-module keys (prefixed with "_")
    return {k: v for k, v in data.items() if not k.startswith("_")}
