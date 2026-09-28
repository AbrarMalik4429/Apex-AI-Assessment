import uuid
from datetime import date, datetime, time, timezone

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Time,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """Normalize writes and comparisons to UTC, including the SQLite test adapter."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("A timezone-aware timestamp is required")
        return value.astimezone(timezone.utc)

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class Base(DeclarativeBase):
    metadata = MetaData(schema="booking")


class Patient(Base):
    __tablename__ = "patient"
    patient_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    patient_name: Mapped[str] = mapped_column(String(120))
    phone_number: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class Doctor(Base):
    __tablename__ = "doctor"
    doctor_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    doctor_name: Mapped[str] = mapped_column(String(120))
    specialty_1: Mapped[str] = mapped_column(String(100))
    specialty_2: Mapped[str | None] = mapped_column(String(100))
    specialty_3: Mapped[str | None] = mapped_column(String(100))


class Slot(Base):
    __tablename__ = "slot"
    slot_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("booking.doctor.doctor_id"))
    day_of_week: Mapped[int] = mapped_column(Integer)  # Monday=0, Sunday=6
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    __table_args__ = (
        CheckConstraint("day_of_week BETWEEN 0 AND 6", name="slot_weekday"),
        CheckConstraint("end_time > start_time", name="slot_time_order"),
        Index("ix_slot_doctor_weekday", "doctor_id", "day_of_week"),
    )


class DoctorLeave(Base):
    __tablename__ = "doctor_leave"
    leave_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("booking.doctor.doctor_id"))
    start_datetime: Mapped[datetime] = mapped_column(UTCDateTime())
    end_datetime: Mapped[datetime] = mapped_column(UTCDateTime())
    reason: Mapped[str | None] = mapped_column(String(250))
    __table_args__ = (
        CheckConstraint("end_datetime > start_datetime", name="leave_time_order"),
        Index("ix_leave_doctor_end", "doctor_id", "end_datetime"),
    )


class Booking(Base):
    __tablename__ = "bookings"
    booking_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("booking.patient.patient_id"))
    doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("booking.doctor.doctor_id"))
    appointment_date: Mapped[date | None] = mapped_column(Date)
    booked_day_of_week: Mapped[int | None] = mapped_column(Integer)
    booked_start_time: Mapped[time | None] = mapped_column(Time)
    booked_end_time: Mapped[time | None] = mapped_column(Time)
    type: Mapped[str] = mapped_column(String(100), default="consultation")
    dependent_on_booking_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("booking.bookings.booking_id")
    )
    superseded_by_booking_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("booking.bookings.booking_id")
    )
    status: Mapped[str] = mapped_column(String(24), default="confirmed")
    notes: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    __table_args__ = (
        CheckConstraint(
            "status IN ('confirmed','pending_scheduling','cancelled','no_show','completed','rescheduled')",
            name="booking_status",
        ),
        CheckConstraint(
            "(appointment_date IS NULL AND booked_day_of_week IS NULL AND booked_start_time IS NULL AND booked_end_time IS NULL) OR (appointment_date IS NOT NULL AND booked_day_of_week IS NOT NULL AND booked_start_time IS NOT NULL AND booked_end_time IS NOT NULL)",
            name="booking_complete_time",
        ),
        CheckConstraint(
            "status != 'confirmed' OR appointment_date IS NOT NULL", name="confirmed_has_time"
        ),
        CheckConstraint(
            "status != 'pending_scheduling' OR appointment_date IS NULL", name="pending_has_no_time"
        ),
        CheckConstraint("booked_end_time > booked_start_time", name="booking_time_order"),
        CheckConstraint("booked_day_of_week BETWEEN 0 AND 6", name="booking_weekday"),
        CheckConstraint("dependent_on_booking_id != booking_id", name="booking_not_own_parent"),
        Index("ix_bookings_doctor_date_status", "doctor_id", "appointment_date", "status"),
        Index("ix_bookings_patient_date_status", "patient_id", "appointment_date", "status"),
        Index("ix_bookings_parent", "dependent_on_booking_id"),
        Index("ix_bookings_replacement", "superseded_by_booking_id"),
    )


class PatientSession(Base):
    __tablename__ = "patient_session"
    session_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("booking.patient.patient_id"))
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime())
    state: Mapped[dict] = mapped_column(JSON, default=dict)
    __table_args__ = (Index("ix_patient_session_patient", "patient_id"),)


class Operation(Base):
    __tablename__ = "operation"
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("booking.patient_session.session_id"), primary_key=True
    )
    request_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    response: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
