"""Dimension tables."""
from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Site(Base, TimestampMixin):
    __tablename__ = "dim_site"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    borough: Mapped[str] = mapped_column(String(100))
    postcode: Mapped[str] = mapped_column(String(12))
    capacity: Mapped[int] = mapped_column(Integer)
    opened_on: Mapped[date | None] = mapped_column(Date)
    monthly_overhead: Mapped[float] = mapped_column(Numeric(12, 2), default=0)

    rooms: Mapped[list["Room"]] = relationship(back_populates="site")


class Room(Base):
    __tablename__ = "dim_room"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("dim_site.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    room_type: Mapped[str] = mapped_column(String(30))  # baby | toddler | preschool
    capacity: Mapped[int] = mapped_column(Integer)
    required_ratio: Mapped[int] = mapped_column(Integer)  # children per staff (EYFS)

    site: Mapped["Site"] = relationship(back_populates="rooms")


class Parent(Base):
    __tablename__ = "dim_parent"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("dim_site.id"))
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(30))


class Child(Base, TimestampMixin):
    __tablename__ = "dim_child"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("dim_site.id"))
    room_id: Mapped[int | None] = mapped_column(ForeignKey("dim_room.id"))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("dim_parent.id"))
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    dob: Mapped[date] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(20))
    enrollment_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20))  # active | withdrawn | waitlist
    funding_type: Mapped[str | None] = mapped_column(String(40))  # private | funded_15 | funded_30
    monthly_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    allergies: Mapped[str | None] = mapped_column(String(255))


class Staff(Base, TimestampMixin):
    __tablename__ = "dim_staff"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("dim_site.id"))
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    role_title: Mapped[str] = mapped_column(String(80))  # Practitioner, Room Leader, Manager...
    qualification_level: Mapped[int] = mapped_column(Integer)  # 0,2,3,6 (EYFS levels)
    dbs_status: Mapped[str] = mapped_column(String(20))  # valid | expiring | expired
    dbs_expiry: Mapped[date | None] = mapped_column(Date)
    contract_hours: Mapped[float] = mapped_column(Numeric(6, 2), default=37.5)
    hourly_rate: Mapped[float] = mapped_column(Numeric(8, 2), default=12.0)
    is_agency: Mapped[bool] = mapped_column(Boolean, default=False)
    employment_status: Mapped[str] = mapped_column(String(20), default="active")


class DimDate(Base):
    __tablename__ = "dim_date"

    date_key: Mapped[date] = mapped_column(Date, primary_key=True)
    year: Mapped[int] = mapped_column(Integer)
    quarter: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    month_name: Mapped[str] = mapped_column(String(12))
    day: Mapped[int] = mapped_column(Integer)
    dow: Mapped[int] = mapped_column(Integer)
    dow_name: Mapped[str] = mapped_column(String(12))
    is_weekend: Mapped[bool] = mapped_column(Boolean)
