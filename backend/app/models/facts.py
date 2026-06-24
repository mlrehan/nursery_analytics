"""Fact tables (transactional / event grain)."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Attendance(Base):
    __tablename__ = "fact_attendance"

    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("dim_child.id"), index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("dim_site.id"), index=True)
    room_id: Mapped[int | None] = mapped_column(ForeignKey("dim_room.id"))
    date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(20))  # present | absent_illness | absent_holiday | unexplained
    check_in: Mapped[datetime | None] = mapped_column(DateTime)
    check_out: Mapped[datetime | None] = mapped_column(DateTime)
    late_pickup: Mapped[bool] = mapped_column(Boolean, default=False)


class EnrollmentEvent(Base):
    __tablename__ = "fact_enrollment_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("dim_child.id"), index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("dim_site.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(30))  # admission | withdrawal | waitlist_join | waitlist_convert | enquiry
    event_date: Mapped[date] = mapped_column(Date, index=True)


class Invoice(Base):
    __tablename__ = "fact_invoice"

    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("dim_child.id"), index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("dim_site.id"), index=True)
    issue_date: Mapped[date] = mapped_column(Date, index=True)
    due_date: Mapped[date] = mapped_column(Date)
    period_month: Mapped[date] = mapped_column(Date, index=True)  # first day of billed month
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    funding_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    discount_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    status: Mapped[str] = mapped_column(String(20))  # paid | unpaid | overdue | partial
    paid_date: Mapped[date | None] = mapped_column(Date)


class Payment(Base):
    __tablename__ = "fact_payment"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("fact_invoice.id"), index=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("dim_child.id"))
    site_id: Mapped[int] = mapped_column(ForeignKey("dim_site.id"), index=True)
    payment_date: Mapped[date] = mapped_column(Date, index=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    method: Mapped[str] = mapped_column(String(20))  # direct_debit | card | bank_transfer
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    is_refund: Mapped[bool] = mapped_column(Boolean, default=False)


class StaffShift(Base):
    __tablename__ = "fact_staff_shift"

    id: Mapped[int] = mapped_column(primary_key=True)
    staff_id: Mapped[int] = mapped_column(ForeignKey("dim_staff.id"), index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("dim_site.id"), index=True)
    room_id: Mapped[int | None] = mapped_column(ForeignKey("dim_room.id"))
    date: Mapped[date] = mapped_column(Date, index=True)
    hours_scheduled: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    hours_worked: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    overtime_hours: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    absent: Mapped[bool] = mapped_column(Boolean, default=False)
    absence_reason: Mapped[str | None] = mapped_column(String(40))


class Incident(Base):
    __tablename__ = "fact_incident"

    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int | None] = mapped_column(ForeignKey("dim_child.id"))
    site_id: Mapped[int] = mapped_column(ForeignKey("dim_site.id"), index=True)
    incident_type: Mapped[str] = mapped_column(String(30))  # accident | incident | safeguarding | medication
    severity: Mapped[str] = mapped_column(String(20))  # low | medium | high
    reported_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(20))  # open | closed
    closed_date: Mapped[date | None] = mapped_column(Date)


class EyfsObservation(Base):
    __tablename__ = "fact_eyfs_observation"

    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("dim_child.id"), index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("dim_site.id"), index=True)
    observation_date: Mapped[date] = mapped_column(Date, index=True)
    area: Mapped[str] = mapped_column(String(30))  # communication | physical | pse | literacy | numeracy
    status: Mapped[str] = mapped_column(String(20))  # emerging | expected | exceeding
    on_track: Mapped[bool] = mapped_column(Boolean, default=True)


class Meal(Base):
    __tablename__ = "fact_meal"

    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("dim_child.id"), index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("dim_site.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    meal_type: Mapped[str] = mapped_column(String(20))  # breakfast | lunch | snack | tea
    intake_pct: Mapped[int] = mapped_column(Integer)  # 0-100
    allergy_flag: Mapped[bool] = mapped_column(Boolean, default=False)


class Message(Base):
    __tablename__ = "fact_message"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("dim_site.id"), index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("dim_parent.id"))
    staff_id: Mapped[int | None] = mapped_column(ForeignKey("dim_staff.id"))
    sent_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    direction: Mapped[str] = mapped_column(String(12))  # inbound | outbound
    message_type: Mapped[str] = mapped_column(String(20))  # report | message | announcement
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    response_minutes: Mapped[int | None] = mapped_column(Integer)
