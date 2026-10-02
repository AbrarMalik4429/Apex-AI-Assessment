from datetime import date, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.booking_service import BookingService
from app.models import Booking, Slot
from app.seed import FOLLOW_UP_ID, OTHER_PATIENT_ID, PATIENT_ID
from tests.conftest import NOW
from tests.test_booking import add_booking, propose, send


def test_database_rejects_same_slot_date_for_another_patient(harness):
    _, factory, _, _ = harness
    add_booking(factory)
    with pytest.raises(IntegrityError):
        add_booking(factory, patient=OTHER_PATIENT_ID)


def test_same_weekly_slot_is_reusable_next_week(harness):
    _, factory, _, _ = harness
    first = add_booking(factory)
    second = add_booking(factory, patient=OTHER_PATIENT_ID, day=date(2026, 10, 15))
    with factory() as db:
        assert db.get(Booking, first).slot_id == db.get(Booking, second).slot_id


def test_cancelled_slot_can_be_booked_by_another_patient(harness):
    _, factory, _, settings = harness
    original = add_booking(factory)
    with factory.begin() as db:
        BookingService(db, settings, PATIENT_ID, NOW).cancel(original)
    replacement = add_booking(factory, patient=OTHER_PATIENT_ID)
    with factory() as db:
        assert db.get(Booking, original).slot_id == db.get(Booking, replacement).slot_id


def test_scheduled_booking_requires_slot_and_pending_followup_has_none(harness):
    _, factory, _, _ = harness
    booking_id = add_booking(factory)
    with factory() as db:
        assert db.get(Booking, FOLLOW_UP_ID).slot_id is None
    with pytest.raises(IntegrityError), factory.begin() as db:
        db.get(Booking, booking_id).slot_id = None
        db.flush()


def test_booking_response_and_followup_persist_selected_slot(harness):
    client, factory, fake, _ = harness
    proposal = propose(client, fake, "follow_up", booking_id=str(FOLLOW_UP_ID))
    result = send(client, "confirm", confirmation_token=proposal["confirmation_token"])
    assert result.json()["status"] == "success"
    with factory() as db:
        booking = db.get(Booking, FOLLOW_UP_ID)
        slot = db.get(Slot, booking.slot_id)
        assert slot.doctor_id == booking.doctor_id
        assert slot.start_time == booking.booked_start_time
        assert result.json()["data"]["booking"]["slot_id"] == str(slot.slot_id)


def test_conflict_after_revalidation_is_reported_without_double_booking(harness, monkeypatch):
    client, factory, fake, _ = harness
    proposal = propose(client, fake)
    add_booking(factory, patient=OTHER_PATIENT_ID)
    # Simulate availability becoming stale after its last read. The actual database
    # index, not the mock, must reject the conflicting INSERT.
    monkeypatch.setattr(BookingService, "revalidate", lambda *args, **kwargs: None)
    result = send(client, "confirm", confirmation_token=proposal["confirmation_token"])
    assert result.status_code == 409
    assert result.json()["data"]["code"] == "slot_unavailable"
    with factory() as db:
        bookings = list(db.scalars(select(Booking).where(Booking.status == "confirmed")))
        assert len(bookings) == 1
        assert bookings[0].patient_id == OTHER_PATIENT_ID


def test_reschedule_constraint_failure_preserves_original(harness, monkeypatch):
    client, factory, fake, _ = harness
    original = add_booking(factory, day=date(2026, 10, 8) + timedelta(days=7))
    proposal = propose(client, fake, "reschedule", booking_id=str(original))
    add_booking(factory, patient=OTHER_PATIENT_ID)
    monkeypatch.setattr(BookingService, "revalidate", lambda *args, **kwargs: None)
    result = send(client, "confirm", confirmation_token=proposal["confirmation_token"])
    assert result.status_code == 409
    with factory() as db:
        old = db.get(Booking, original)
        assert old.status == "confirmed"
        assert old.superseded_by_booking_id is None


def test_same_slot_date_reschedule_is_rejected_before_proposal(harness):
    from tests.conftest import intent

    client, factory, fake, _ = harness
    original = add_booking(factory)
    fake.queue.append(
        intent(
            "reschedule",
            booking_id=str(original),
            appointment_date="2026-10-08",
            start_time="09:00",
        )
    )
    result = send(client, f"Reschedule booking {original} to the same time").json()
    assert result["data"]["code"] == "same_appointment_time"
    assert result["confirmation_token"] is None
    with factory() as db:
        assert db.get(Booking, original).status == "confirmed"
        assert db.get(Booking, original).superseded_by_booking_id is None


def test_same_slot_date_is_hidden_and_rejected_at_write(harness):
    from app.contracts import Candidate, DomainError

    client, factory, _, settings = harness
    original = add_booking(factory)
    with factory.begin() as db:
        old = db.get(Booking, original)
        service = BookingService(db, settings, PATIENT_ID, NOW)
        options = service.availability(
            old.doctor_id, old.appointment_date, old.appointment_date, original
        )
        assert all(c.slot_id != old.slot_id for c in options)
        candidate = Candidate(
            doctor_id=old.doctor_id,
            doctor_name="Dr. Amal Demo",
            slot_id=old.slot_id,
            appointment_date=old.appointment_date,
            start_time=old.booked_start_time,
            end_time=old.booked_end_time,
        )
        with pytest.raises(DomainError) as error:
            service.reschedule(original, candidate)
        assert error.value.code == "same_appointment_time"
        assert old.status == "confirmed"
        # Same recurring template on another matching date remains valid.
        candidate.appointment_date += timedelta(days=7)
        replacement = service.reschedule(original, candidate)
        assert replacement.slot_id == old.slot_id
        assert replacement.appointment_date != old.appointment_date
