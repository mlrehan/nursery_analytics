"""Global search across dashboards, sites, children and staff — role-scoped."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.common import scope_for
from app.core.database import get_db
from app.core.deps import get_current_user, get_user_permissions
from app.models.auth import User

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
async def search(
    q: str = Query(..., min_length=1),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    term = q.strip()
    like = f"%{term}%"
    scope = scope_for(user)
    perms = await get_user_permissions(user, db)

    # 1) Dashboards the user is allowed to open
    modrows = (await db.execute(text(
        "SELECT key, name FROM dashboard_modules WHERE name ILIKE :like ORDER BY sort_order LIMIT 8"
    ), {"like": like})).all()
    modules = [{"key": r.key, "name": r.name} for r in modrows if f"view.{r.key}" in perms]

    sites, children, staff = [], [], []

    # 2) Sites (privileged roles, or the user's own site)
    site_filter = " AND id = :sid " if scope.site_id else ""
    siterows = (await db.execute(text(
        f"SELECT id, name, borough FROM dim_site WHERE (name ILIKE :like OR borough ILIKE :like){site_filter} ORDER BY name LIMIT 6"
    ), {"like": like, **({"sid": scope.site_id} if scope.site_id else {})})).all()
    sites = [{"id": r.id, "name": r.name, "borough": r.borough} for r in siterows]

    # 3) Children (scoped: site for teachers, single child for parents)
    child_filter = ""
    params = {"like": like}
    if scope.child_id:
        child_filter = " AND c.id = :cid "
        params["cid"] = scope.child_id
    elif scope.site_id:
        child_filter = " AND c.site_id = :sid "
        params["sid"] = scope.site_id
    childrows = (await db.execute(text(
        f"""SELECT c.id, c.first_name||' '||c.last_name AS name, r.name AS room, c.status
            FROM dim_child c LEFT JOIN dim_room r ON r.id = c.room_id
            WHERE (c.first_name ILIKE :like OR c.last_name ILIKE :like){child_filter}
            ORDER BY c.last_name LIMIT 6"""
    ), params)).all()
    children = [{"id": r.id, "name": r.name, "room": r.room, "status": r.status} for r in childrows]

    # 4) Staff (not exposed to parents)
    if user.role and user.role.slug != "parent":
        sparams = {"like": like}
        staff_filter = ""
        if scope.site_id:
            staff_filter = " AND site_id = :sid "
            sparams["sid"] = scope.site_id
        staffrows = (await db.execute(text(
            f"""SELECT id, first_name||' '||last_name AS name, role_title
                FROM dim_staff WHERE (first_name ILIKE :like OR last_name ILIKE :like OR role_title ILIKE :like){staff_filter}
                ORDER BY last_name LIMIT 6"""
        ), sparams)).all()
        staff = [{"id": r.id, "name": r.name, "role": r.role_title} for r in staffrows]

    total = len(modules) + len(sites) + len(children) + len(staff)
    return {"query": term, "total": total, "modules": modules, "sites": sites,
            "children": children, "staff": staff}
