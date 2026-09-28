"""Synthetic doctor-side fixtures; not a patient-facing schedule-writing API."""

from datetime import datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.config import Settings
from app.db import make_engine, make_session_factory
from app.models import Booking, Doctor, DoctorLeave, Patient, Slot, utcnow

PATIENT_ID = UUID("00000000-0000-0000-0000-000000000001")
OTHER_PATIENT_ID = UUID("00000000-0000-0000-0000-000000000002")
DOCTOR_1 = UUID("10000000-0000-0000-0000-000000000001")
DOCTOR_2 = UUID("10000000-0000-0000-0000-000000000002")
PARENT_ID = UUID("20000000-0000-0000-0000-000000000001")
FOLLOW_UP_ID = UUID("20000000-0000-0000-0000-000000000002")


def seed(db, settings: Settings, now=None):
    if db.get(Patient, PATIENT_ID):
        return False
    if db.scalar(select(Patient.patient_id).limit(1)):
        raise RuntimeError("Use a dedicated empty demo database for synthetic data.")
    today = (now or utcnow()).astimezone(ZoneInfo(settings.clinic_timezone)).date()
    db.add_all(
        [
            Patient(
                patient_id=PATIENT_ID, patient_name="Demo Patient", phone_number="synthetic-001"
            ),
            Patient(
                patient_id=OTHER_PATIENT_ID,
                patient_name="Other Demo Patient",
                phone_number="synthetic-002",
            ),
            Doctor(doctor_id=DOCTOR_1, doctor_name="Dr. Amal Demo", specialty_1="dermatology"),
            Doctor(doctor_id=DOCTOR_2, doctor_name="Dr. Sami Demo", specialty_1="general medicine"),
        ]
    )
    db.flush()
    for doctor_id in [DOCTOR_1, DOCTOR_2]:
        for weekday in range(7):
            for hour, minute in [(9, 0), (9, 30), (10, 0), (10, 30), (14, 0), (14, 30)]:
                start = time(hour, minute)
                end = time(hour + (minute + 30) // 60, (minute + 30) % 60)
                db.add(
                    Slot(doctor_id=doctor_id, day_of_week=weekday, start_time=start, end_time=end)
                )
    past = today - timedelta(days=14)
    db.add(
        Booking(
            booking_id=PARENT_ID,
            patient_id=PATIENT_ID,
            doctor_id=DOCTOR_1,
            appointment_date=past,
            booked_day_of_week=past.weekday(),
            booked_start_time=time(9),
            booked_end_time=time(9, 30),
            type="consultation",
            status="completed",
        )
    )
    db.flush()
    db.add(
        Booking(
            booking_id=FOLLOW_UP_ID,
            patient_id=PATIENT_ID,
            doctor_id=DOCTOR_1,
            type="follow-up",
            dependent_on_booking_id=PARENT_ID,
            status="pending_scheduling",
        )
    )
    leave_day = today + timedelta(days=4)
    zone = ZoneInfo(settings.clinic_timezone)
    db.add(
        DoctorLeave(
            doctor_id=DOCTOR_1,
            start_datetime=datetime.combine(leave_day, time(9), zone),
            end_datetime=datetime.combine(leave_day, time(10), zone),
            reason="Synthetic leave",
        )
    )
    return True


if __name__ == "__main__":
    config = Settings()
    if not config.demo_enabled:
        raise SystemExit("Set DEMO_ENABLED=true only for a synthetic demo environment.")
    factory = make_session_factory(make_engine(config))
    with factory.begin() as session:
        inserted = seed(session, config)
    print(
        "Synthetic seed loaded." if inserted else "Synthetic seed already exists; no changes made."
    )
