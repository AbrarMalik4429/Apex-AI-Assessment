from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.contracts import Candidate, DomainError
from app.models import Booking, Doctor, DoctorLeave, Slot


def aware(value: datetime) -> datetime:
    # SQLite loses tzinfo in tests. PostgreSQL preserves timestamptz offsets.
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def booking_data(booking: Booking) -> dict:
    return {
        "booking_id": str(booking.booking_id),
        "doctor_id": str(booking.doctor_id),
        "slot_id": str(booking.slot_id) if booking.slot_id else None,
        "appointment_date": booking.appointment_date.isoformat()
        if booking.appointment_date
        else None,
        "start_time": booking.booked_start_time.isoformat() if booking.booked_start_time else None,
        "end_time": booking.booked_end_time.isoformat() if booking.booked_end_time else None,
        "type": booking.type,
        "status": booking.status,
        "dependent_on_booking_id": str(booking.dependent_on_booking_id)
        if booking.dependent_on_booking_id
        else None,
        "superseded_by_booking_id": str(booking.superseded_by_booking_id)
        if booking.superseded_by_booking_id
        else None,
    }


class BookingService:
    """All authorization and business decisions are deterministic; never commit here."""

    def __init__(self, db: Session, settings: Settings, patient_id: UUID, now: datetime):
        self.db, self.settings, self.patient_id = db, settings, patient_id
        self.now = aware(now)
        self.zone = ZoneInfo(settings.clinic_timezone)

    def doctors(self, query: str | None = None, specialty: str | None = None) -> list[Doctor]:
        doctors = list(self.db.scalars(select(Doctor).order_by(Doctor.doctor_name)))
        if query and query.casefold().strip() == "previous":
            previous = self.db.scalar(
                select(Booking)
                .where(Booking.patient_id == self.patient_id, Booking.status == "completed")
                .order_by(Booking.appointment_date.desc(), Booking.created_at.desc())
                .limit(1)
            )
            return [d for d in doctors if previous and d.doctor_id == previous.doctor_id]
        if query:
            q = query.casefold().strip()
            doctors = [d for d in doctors if q in d.doctor_name.casefold() or q == str(d.doctor_id)]
        if specialty:
            q = specialty.casefold().strip()
            doctors = [
                d
                for d in doctors
                if any(
                    q in s.casefold() for s in (d.specialty_1, d.specialty_2, d.specialty_3) if s
                )
            ]
        return doctors

    def lookup(self, booking_id: UUID) -> Booking:
        booking = self.db.scalar(
            select(Booking).where(
                Booking.booking_id == booking_id, Booking.patient_id == self.patient_id
            )
        )
        if booking is None:
            # Do not reveal whether another patient's ID exists.
            raise DomainError(
                "booking_not_found", "No matching appointment was found for your session."
            )
        return booking

    def appointments(self) -> list[Booking]:
        return list(
            self.db.scalars(
                select(Booking)
                .where(Booking.patient_id == self.patient_id)
                .order_by(Booking.created_at.desc(), Booking.booking_id)
            )
        )

    def interval(self, booking: Booking) -> tuple[datetime, datetime]:
        if booking.appointment_date is None:
            raise DomainError("unscheduled", "This appointment does not have a scheduled time.")
        return (
            datetime.combine(booking.appointment_date, booking.booked_start_time, self.zone),
            datetime.combine(booking.appointment_date, booking.booked_end_time, self.zone),
        )

    def availability(
        self,
        doctor_id: UUID,
        start: date | None = None,
        end: date | None = None,
        exclude_booking_id: UUID | None = None,
        limit: int | None = 20,
    ) -> list[Candidate]:
        doctor = self.db.get(Doctor, doctor_id)
        if doctor is None:
            raise DomainError("doctor_not_found", "That doctor was not found.")
        today = self.now.astimezone(self.zone).date()
        horizon = today + timedelta(days=self.settings.booking_horizon_days)
        start, end = start or today, end or horizon
        if start < today or end > horizon or end < start:
            raise DomainError("invalid_window", f"Choose dates between {today} and {horizon}.")
        if exclude_booking_id is not None:
            excluded = self.lookup(exclude_booking_id)
            if excluded.status != "confirmed":
                raise DomainError(
                    "invalid_status", "Only a confirmed appointment can be rescheduled."
                )
        slots = list(
            self.db.scalars(
                select(Slot).where(Slot.doctor_id == doctor_id).order_by(Slot.start_time)
            )
        )
        leaves = list(
            self.db.scalars(
                select(DoctorLeave).where(
                    DoctorLeave.doctor_id == doctor_id,
                    DoctorLeave.end_datetime > datetime.combine(start, time.min, self.zone),
                    DoctorLeave.start_datetime
                    < datetime.combine(end + timedelta(days=1), time.min, self.zone),
                )
            )
        )
        query = select(Booking).where(
            Booking.status == "confirmed",
            Booking.appointment_date.between(start, end),
            or_(Booking.doctor_id == doctor_id, Booking.patient_id == self.patient_id),
        )
        if exclude_booking_id:
            query = query.where(Booking.booking_id != exclude_booking_id)
        occupied = [self.interval(b) for b in self.db.scalars(query)]
        result = []
        day = start
        while day <= end:
            for slot in slots:
                if slot.day_of_week != day.weekday():
                    continue
                candidate_start = datetime.combine(day, slot.start_time, self.zone)
                candidate_end = datetime.combine(day, slot.end_time, self.zone)
                if candidate_start <= self.now:
                    continue
                if any(
                    aware(leave.start_datetime) < candidate_end
                    and aware(leave.end_datetime) > candidate_start
                    for leave in leaves
                ):
                    continue
                if any(a < candidate_end and b > candidate_start for a, b in occupied):
                    continue
                result.append(
                    Candidate(
                        doctor_id=doctor_id,
                        doctor_name=doctor.doctor_name,
                        slot_id=slot.slot_id,
                        appointment_date=day,
                        start_time=slot.start_time,
                        end_time=slot.end_time,
                    )
                )
                if limit and len(result) >= limit:
                    return result
            day += timedelta(days=1)
        return result

    def revalidate(self, candidate: Candidate, exclude: UUID | None = None) -> None:
        available = self.availability(
            candidate.doctor_id,
            candidate.appointment_date,
            candidate.appointment_date,
            exclude,
            limit=None,
        )
        if not any(
            c.slot_id == candidate.slot_id
            and c.start_time == candidate.start_time
            and c.end_time == candidate.end_time
            for c in available
        ):
            raise DomainError(
                "slot_unavailable",
                "That time is no longer available. Please choose another time.",
                "unavailable",
            )

    def apply_time(self, booking: Booking, candidate: Candidate) -> None:
        booking.slot_id = candidate.slot_id
        booking.appointment_date = candidate.appointment_date
        booking.booked_day_of_week = candidate.appointment_date.weekday()
        booking.booked_start_time = candidate.start_time
        booking.booked_end_time = candidate.end_time
        booking.status = "confirmed"

    def book(self, candidate: Candidate, appointment_type: str) -> Booking:
        self.revalidate(candidate)
        booking = Booking(
            patient_id=self.patient_id, doctor_id=candidate.doctor_id, type=appointment_type
        )
        self.apply_time(booking, candidate)
        self.db.add(booking)
        self.db.flush()
        return booking

    def check_change(self, booking: Booking, action: str) -> None:
        if booking.status != "confirmed":
            raise DomainError("invalid_status", "Only confirmed appointments can be changed.")
        start, _ = self.interval(booking)
        if start <= self.now:
            raise DomainError("past_appointment", "Past appointments cannot be changed here.")
        hours = (
            self.settings.cancellation_notice_hours
            if action == "cancel"
            else self.settings.reschedule_notice_hours
        )
        if start - self.now <= timedelta(hours=hours):
            raise DomainError(
                "notice_policy",
                f"This change requires human approval because the appointment is within {hours} hours. No change was made and no approval request was submitted.",
                "requires_approval",
            )

    def cancel(self, booking_id: UUID) -> Booking:
        booking = self.lookup(booking_id)
        if booking.status == "cancelled":
            return booking
        self.check_change(booking, "cancel")
        booking.status = "cancelled"
        self.db.flush()
        return booking

    def reschedule(self, booking_id: UUID, candidate: Candidate) -> Booking:
        old = self.lookup(booking_id)
        self.check_change(old, "reschedule")
        if old.doctor_id != candidate.doctor_id:
            raise DomainError(
                "doctor_change",
                "Rescheduling keeps the same doctor. Make a separate booking to change doctors.",
            )
        self.revalidate(candidate, old.booking_id)
        new = Booking(
            patient_id=self.patient_id,
            doctor_id=old.doctor_id,
            type=old.type,
            notes=old.notes,
            dependent_on_booking_id=old.dependent_on_booking_id,
        )
        self.apply_time(new, candidate)
        # Release the old key before inserting, including a same-slot reschedule.
        # Both changes remain in the enclosing transaction and roll back together.
        old.status = "rescheduled"
        self.db.flush()
        self.db.add(new)
        self.db.flush()
        old.superseded_by_booking_id = new.booking_id
        self.db.flush()
        return new

    def schedule_follow_up(self, booking_id: UUID, candidate: Candidate) -> Booking:
        booking = self.lookup(booking_id)
        if booking.status != "pending_scheduling" or booking.dependent_on_booking_id is None:
            raise DomainError("invalid_follow_up", "Choose an existing unscheduled follow-up.")
        self.lookup(booking.dependent_on_booking_id)  # Same-patient relationship.
        if booking.doctor_id != candidate.doctor_id:
            raise DomainError("doctor_change", "The follow-up must use its assigned doctor.")
        self.revalidate(candidate)
        self.apply_time(booking, candidate)
        self.db.flush()
        return booking
