"""ORM models aligned to the SQL migration schema."""
from app.models.base import Base
from app.models.auth import (
    Role,
    Permission,
    RolePermission,
    User,
    DashboardModule,
    DashboardWidget,
    RoleWidgetAccess,
)
from app.models.dimensions import Site, Room, Child, Parent, Staff, DimDate
from app.models.settings import AppSettings
from app.models.share import ShareLink
from app.models.facts import (
    Attendance,
    EnrollmentEvent,
    Invoice,
    Payment,
    StaffShift,
    Incident,
    EyfsObservation,
    Meal,
    Message,
)

__all__ = [
    "Base",
    "Role",
    "Permission",
    "RolePermission",
    "User",
    "DashboardModule",
    "DashboardWidget",
    "RoleWidgetAccess",
    "Site",
    "Room",
    "Child",
    "Parent",
    "Staff",
    "DimDate",
    "AppSettings",
    "ShareLink",
    "Attendance",
    "EnrollmentEvent",
    "Invoice",
    "Payment",
    "StaffShift",
    "Incident",
    "EyfsObservation",
    "Meal",
    "Message",
]
