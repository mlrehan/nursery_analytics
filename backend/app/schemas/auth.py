"""Auth + dashboard-config Pydantic schemas (v2)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    name: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    full_name: str
    role: RoleOut
    site_id: int | None = None
    is_active: bool
    last_login_at: datetime | None = None


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role_id: int
    site_id: int | None = None


# ─── Dashboard config ─────────────────────────────────────────────────────────
class WidgetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    key: str
    title: str
    viz_type: str
    description: str | None = None
    span: int
    sort_order: int


class ModuleWithWidgets(BaseModel):
    key: str
    name: str
    icon: str | None = None
    description: str | None = None
    sort_order: int
    widgets: list[WidgetOut]


class MeDashboard(BaseModel):
    """What the logged-in user is allowed to see."""
    user: UserOut
    permissions: list[str]
    modules: list[ModuleWithWidgets]


class RoleWidgetToggle(BaseModel):
    role_id: int
    widget_key: str
    is_enabled: bool
