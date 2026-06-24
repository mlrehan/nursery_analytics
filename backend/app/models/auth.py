"""RBAC + dashboard-composition models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)

    permissions: Mapped[list["RolePermission"]] = relationship(back_populates="role", cascade="all, delete-orphan")
    users: Mapped[list["User"]] = relationship(back_populates="role")


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"))
    permission_id: Mapped[int] = mapped_column(ForeignKey("permissions.id", ondelete="CASCADE"))

    role: Mapped["Role"] = relationship(back_populates="permissions")
    permission: Mapped["Permission"] = relationship()


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(150))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    site_id: Mapped[int | None] = mapped_column(ForeignKey("dim_site.id"))
    # When a user is a parent/teacher tied to specific records:
    linked_child_id: Mapped[int | None] = mapped_column(ForeignKey("dim_child.id"))
    linked_staff_id: Mapped[int | None] = mapped_column(ForeignKey("dim_staff.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column()
    # profile (self-service)
    phone: Mapped[str | None] = mapped_column(String(40))
    job_title: Mapped[str | None] = mapped_column(String(120))
    address: Mapped[str | None] = mapped_column(Text)
    about: Mapped[str | None] = mapped_column(Text)
    avatar_url: Mapped[str | None] = mapped_column(Text)

    role: Mapped["Role"] = relationship(back_populates="users")


class DashboardModule(Base):
    """One of the 15 dashboard areas (Executive, Occupancy, Finance, ...)."""

    __tablename__ = "dashboard_modules"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    icon: Mapped[str | None] = mapped_column(String(60))
    description: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    widgets: Mapped[list["DashboardWidget"]] = relationship(back_populates="module", cascade="all, delete-orphan")


class DashboardWidget(Base):
    """A single KPI / chart within a module, with a backing API endpoint."""

    __tablename__ = "dashboard_widgets"

    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("dashboard_modules.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(150))
    # viz_type: kpi | line | bar | stacked_bar | pie | heatmap | gauge | table | funnel
    viz_type: Mapped[str] = mapped_column(String(40))
    description: Mapped[str | None] = mapped_column(Text)
    # grid sizing hints for the frontend
    span: Mapped[int] = mapped_column(Integer, default=4)  # out of 12 columns
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    module: Mapped["DashboardModule"] = relationship(back_populates="widgets")


class RoleWidgetAccess(Base):
    """Admin-controlled: which widgets each role sees on its dashboard.

    A row that is enabled => the role sees that widget. Defaults are seeded per
    role; admins add/remove rows to customise.
    """

    __tablename__ = "role_widget_access"
    __table_args__ = (UniqueConstraint("role_id", "widget_id", name="uq_role_widget"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"))
    widget_id: Mapped[int] = mapped_column(ForeignKey("dashboard_widgets.id", ondelete="CASCADE"))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
